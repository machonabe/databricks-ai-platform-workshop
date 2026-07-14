"""Vehicle Agent App - OEM Connected Vehicle Dashboard"""
import os, time, logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GENIE_SPACE_ID = os.environ.get("GENIE_SPACE_ID", "")
FMAPI_MODEL = os.environ.get("FMAPI_MODEL", "databricks-meta-llama-3-3-70b-instruct")
CATALOG = os.environ.get("CATALOG", "main")
SCHEMA = os.environ.get("SCHEMA", "ai_workshop")

app = FastAPI(title="Vehicle Agent API")
w = WorkspaceClient()

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    answer: str
    source: str
    latency_sec: float
    sql: str | None = None

class VehicleStatus(BaseModel):
    vehicle_id: str
    model: str
    battery_pct: float
    range_km: float
    battery_temp_c: float
    last_trip_km: float
    efficiency_kwh_per_km: float


def ask_genie(question: str) -> dict:
    if not GENIE_SPACE_ID:
        return {"error": "GENIE_SPACE_ID not configured"}
    try:
        conv = w.genie.start_conversation(space_id=GENIE_SPACE_ID, content=question)
        for _ in range(15):
            msg = w.genie.get_message(space_id=GENIE_SPACE_ID,
                conversation_id=conv.conversation_id, message_id=conv.message_id)
            if msg.status == "COMPLETED":
                break
            if msg.status in ("FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"):
                return {"error": f"Genie status: {msg.status}"}
            time.sleep(2)
        result = {}
        if msg.attachments:
            for att in msg.attachments:
                if att.text:
                    result["answer_text"] = att.text.content
                if att.query:
                    result["sql"] = att.query.query
                    try:
                        qr = w.genie.get_message_query_result(space_id=GENIE_SPACE_ID,
                            conversation_id=conv.conversation_id,
                            message_id=conv.message_id, attachment_id=att.id)
                        result["columns"] = [c.name for c in qr.statement_response.manifest.schema.columns]
                        result["rows"] = qr.statement_response.result.data_array[:10] if qr.statement_response.result else []
                    except Exception:
                        pass
        return result
    except Exception as e:
        return {"error": str(e)}


def _query_tables_directly(question: str) -> dict | None:
    """Genie 失敗時 fallback: LLM で SQL 生成 + SQL Statement API で実行"""
    try:
        schema_info = (f"Tables: {CATALOG}.{SCHEMA}.vehicles (vehicle_id,model,battery_capacity_kwh,manufactured_year), "
                       f"{CATALOG}.{SCHEMA}.trip_logs (trip_id,vehicle_id,trip_date,distance_km,energy_consumed_kwh,avg_speed_kmh,battery_temp_start_c,efficiency_km_per_kwh)")
        sql_prompt = f"Write a Databricks SQL SELECT query to answer: {question}. Schema: {schema_info}. Return ONLY the SQL, no explanation."
        resp = w.serving_endpoints.query(name=FMAPI_MODEL,
            messages=[ChatMessage(role=ChatMessageRole.USER, content=sql_prompt)], max_tokens=300)
        sql = (resp.choices[0].message.content or "").strip()
        if sql.startswith("```"): sql = sql.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if not sql.upper().startswith("SELECT"): return None

        from databricks.sdk.service.sql import StatementState
        wh_list = list(w.warehouses.list())
        if not wh_list: return None
        stmt = w.statement_execution.execute_statement(warehouse_id=wh_list[0].id, statement=sql, wait_timeout="30s")
        if stmt.status.state != StatementState.SUCCEEDED: return None

        cols = [c.name for c in stmt.manifest.schema.columns]
        rows = stmt.result.data_array[:10] if stmt.result and stmt.result.data_array else []
        if not rows: return None
        context = "\n".join([str(dict(zip(cols, r))) for r in rows])

        resp2 = w.serving_endpoints.query(name=FMAPI_MODEL,
            messages=[ChatMessage(role=ChatMessageRole.USER,
                content=f"以下のデータを元に日本語で回答。数値はそのまま使用。\n質問:{question}\nデータ:{context}")], max_tokens=500)
        return {"answer": resp2.choices[0].message.content or context, "sql": sql}
    except Exception:
        return None


def vehicle_agent(question: str) -> tuple[str, str, str | None]:
    # 分類ステップを廃止し、まず Genie/SQL Direct を試す（高速化）
    if GENIE_SPACE_ID:
        genie_result = ask_genie(question)
        sql = genie_result.get("sql")
        if not genie_result.get("error"):
            if genie_result.get("answer_text"):
                context = genie_result["answer_text"]
            elif genie_result.get("rows"):
                cols = genie_result.get("columns", [])
                context = "\n".join([str(dict(zip(cols, r))) for r in genie_result["rows"][:10]])
            else:
                context = None
            if context:
                resp = w.serving_endpoints.query(name=FMAPI_MODEL,
                    messages=[ChatMessage(role=ChatMessageRole.USER,
                        content=f"以下のデータを元に日本語で回答。数値はそのまま。\n質問:{question}\nデータ:{context}")], max_tokens=500)
                return (resp.choices[0].message.content or context[:300]), "Genie", sql

    # Genie 失敗/未設定 → SQL Direct
    sql_result = _query_tables_directly(question)
    if sql_result:
        return sql_result["answer"], "SQL Direct", sql_result.get("sql")

    # 最終 fallback: FMAPI 直接
    return _call_fmapi(question), "FMAPI", None


def _call_fmapi(question: str) -> str:
    try:
        resp = w.serving_endpoints.query(name=FMAPI_MODEL,
            messages=[ChatMessage(role=ChatMessageRole.USER,
                content=f"車両テレメトリ AIアシスタントとして日本語で回答。\n質問:{question}")], max_tokens=500)
        return resp.choices[0].message.content or "回答を生成できませんでした"
    except Exception as e:
        return f"エラー: {str(e)[:200]}"


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        start = time.time()
        answer, source, sql = vehicle_agent(req.message)
        return ChatResponse(answer=answer or "回答取得失敗", source=source, latency_sec=round(time.time()-start, 2), sql=sql)
    except Exception as e:
        return ChatResponse(answer=f"システムエラー: {str(e)[:100]}", source="Error", latency_sec=0, sql=None)

@app.get("/api/vehicle/{vehicle_id}", response_model=VehicleStatus)
async def get_vehicle_status(vehicle_id: str):
    import random
    vehicles = {"V-001":("EV-Civic",64.0),"V-002":("EV-Accord",82.0),"V-003":("EV-CR-V",78.5),"V-004":("EV-Pilot",95.0),"V-005":("EV-Odyssey",100.0)}
    if vehicle_id not in vehicles: raise HTTPException(status_code=404, detail="Vehicle not found")
    model, batt = vehicles[vehicle_id]
    pct = random.uniform(40,95); eff = random.uniform(0.14,0.22)
    return VehicleStatus(vehicle_id=vehicle_id, model=model, battery_pct=round(pct,1),
        range_km=round(batt*(pct/100)/eff,0), battery_temp_c=round(random.uniform(22,38),1),
        last_trip_km=round(random.uniform(5,80),1), efficiency_kwh_per_km=round(eff,3))

@app.get("/api/vehicles")
async def list_vehicles():
    return [{"vehicle_id":f"V-00{i}","model":m,"year":y} for i,(m,y) in enumerate([("EV-Civic",2024),("EV-Accord",2024),("EV-CR-V",2025),("EV-Pilot",2025),("EV-Odyssey",2025)],1)]

@app.get("/api/health")
async def health():
    return {"status":"ok","genie_space_id":GENIE_SPACE_ID or "NOT SET","fmapi_model":FMAPI_MODEL}

static_dir = Path(__file__).parent / "static"
if static_dir.exists(): app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def root(): return FileResponse(str(static_dir / "index.html"))

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8000)