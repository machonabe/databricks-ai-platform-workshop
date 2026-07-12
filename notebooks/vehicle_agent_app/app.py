"""Vehicle Agent App - OEM-style Connected Vehicle Dashboard
FastAPI backend + React TypeScript frontend
"""
import os
import time
import json
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Config ---
GENIE_SPACE_ID = os.environ.get("GENIE_SPACE_ID", "")
FMAPI_MODEL = os.environ.get("FMAPI_MODEL", "databricks-meta-llama-3-3-70b-instruct")
CATALOG = os.environ.get("CATALOG", "main")
SCHEMA = os.environ.get("SCHEMA", "ai_workshop")

app = FastAPI(title="Vehicle Agent API")
w = WorkspaceClient()

# --- Models ---
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


# --- Genie Helper ---
def ask_genie(question: str) -> dict:
    if not GENIE_SPACE_ID:
        logger.warning("GENIE_SPACE_ID is empty")
        return {"error": "GENIE_SPACE_ID not configured"}
    try:
        logger.info(f"Calling Genie Space: {GENIE_SPACE_ID}")
        conv = w.genie.start_conversation(space_id=GENIE_SPACE_ID, content=question)
        for _ in range(12):
            msg = w.genie.get_message(
                space_id=GENIE_SPACE_ID,
                conversation_id=conv.conversation_id,
                message_id=conv.message_id
            )
            if msg.status == "COMPLETED":
                break
            time.sleep(5)
        result = {}
        if msg.attachments:
            for att in msg.attachments:
                if att.text:
                    result["answer_text"] = att.text.content
                if att.query:
                    result["sql"] = att.query.query
                    result["description"] = att.query.description
                    try:
                        qr = w.genie.get_message_query_result(
                            space_id=GENIE_SPACE_ID,
                            conversation_id=conv.conversation_id,
                            message_id=conv.message_id,
                            attachment_id=att.id
                        )
                        cols = [c.name for c in qr.statement_response.manifest.schema.columns]
                        rows = qr.statement_response.result.data_array[:10] if qr.statement_response.result else []
                        result["columns"] = cols
                        result["rows"] = rows
                    except Exception as qe:
                        logger.error(f"Query result fetch error: {qe}")
        logger.info(f"Genie result keys: {list(result.keys())}")
        return result
    except Exception as e:
        logger.error(f"Genie API error: {e}")
        return {"error": str(e)}


# --- Agent Logic ---
def vehicle_agent(question: str) -> tuple[str, str, str | None]:
    """Returns (answer, source, sql)"""
    # Classify - improved prompt
    classify_resp = w.serving_endpoints.query(
        name=FMAPI_MODEL,
        messages=[ChatMessage(
            role=ChatMessageRole.USER,
            content=(
                "以下の質問を分類してください。\n"
                "車両の走行データ・電費・距離・バッテリー温度・車種比較・回生量・走行ログ・"
                "速度・エネルギー消費など「実データベースを参照すれば答えられる」質問なら DATA とだけ答えてください。\n"
                "それ以外（一般知識、仕組みの説明、アドバイス、定義）なら GENERAL とだけ答えてください。\n\n"
                f"質問: {question}\n分類:"
            )
        )],
        max_tokens=10
    )
    raw_category = classify_resp.choices[0].message.content
    category = (raw_category or "").strip().upper()
    if not category:
        category = "DATA"  # 分類失敗時は DATA とみなして Genie を試す
    logger.info(f"Classification: '{category}' for question: '{question}'")

    if "DATA" in category and GENIE_SPACE_ID:
        genie_result = ask_genie(question)
        sql = genie_result.get("sql")

        if genie_result.get("error"):
            logger.warning(f"Genie failed: {genie_result['error']}, trying SQL fallback")
            # Genie 失敗時: SQL Statement API で直接データ取得を試みる
            sql_result = _query_tables_directly(question)
            if sql_result:
                return sql_result["answer"], "SQL Direct", sql_result.get("sql")
            answer = _call_fmapi_with_context(question)
            return answer, "FMAPI (Genie unavailable)", sql

        if genie_result.get("answer_text"):
            context = genie_result["answer_text"]
        elif genie_result.get("rows"):
            cols = genie_result.get("columns", [])
            rows_str = "\n".join([str(dict(zip(cols, r))) for r in genie_result["rows"][:10]])
            context = f"クエリ結果:\n{rows_str}"
        else:
            # Genie returned no useful data
            answer = _call_fmapi_with_context(question)
            return answer, "FMAPI (データ取得失敗)", sql

        # Summarize with LLM (SYSTEM role を避けて USER に統合)
        summarize_prompt = (
            "以下のデータを元に、質問に日本語で分かりやすく回答してください。"
            "数値はそのまま使用してください。\n\n"
            f"質問: {question}\n\nデータ: {context}"
        )
        resp = w.serving_endpoints.query(
            name=FMAPI_MODEL,
            messages=[ChatMessage(role=ChatMessageRole.USER, content=summarize_prompt)],
            max_tokens=500
        )
        answer = resp.choices[0].message.content
        if not answer:
            answer = f"データは取得できましたが要約に失敗。\n生データ: {context[:300]}"
        return answer, "Genie", sql
    else:
        answer = _call_fmapi_with_context(question)
        return answer, "FMAPI", None


def _call_fmapi_with_context(question: str) -> str:
    """FMAPI で回答（車両コンテキスト付き）"""
    try:
        # Gemini Flash は SYSTEM role で content=None を返す場合があるため
        # USER メッセージにコンテキストを統合する
        combined_prompt = (
            "あなたは車両テレメトリ AI アシスタントです。"
            "EV の電費、バッテリー、走行距離について専門知識を持っています。"
            "質問に日本語で丁寧に回答してください。\n\n"
            f"質問: {question}"
        )
        resp = w.serving_endpoints.query(
            name=FMAPI_MODEL,
            messages=[
                ChatMessage(role=ChatMessageRole.USER, content=combined_prompt)
            ],
            max_tokens=500
        )
        answer = resp.choices[0].message.content
        if not answer:
            # リトライ: シンプルなプロンプトで再試行
            logger.warning("First FMAPI call returned empty, retrying with simple prompt")
            resp2 = w.serving_endpoints.query(
                name=FMAPI_MODEL,
                messages=[ChatMessage(role=ChatMessageRole.USER, content=question)],
                max_tokens=500
            )
            answer = resp2.choices[0].message.content
        if not answer:
            return f"回答を生成できませんでした。質問を言い換えてお試しください。(model: {FMAPI_MODEL})"
        return answer
    except Exception as e:
        logger.error(f"FMAPI call failed: {e}")
        return f"エラーが発生しました: {str(e)[:200]}"


# --- API Endpoints ---
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        start = time.time()
        answer, source, sql = vehicle_agent(req.message)
        elapsed = time.time() - start
        # Ensure answer is never empty
        if not answer:
            answer = "回答を取得できませんでした。"
        return ChatResponse(answer=answer, source=source, latency_sec=round(elapsed, 2), sql=sql)
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return ChatResponse(
            answer=f"システムエラーが発生しました。管理者にお問い合わせください。\n({str(e)[:100]})",
            source="Error",
            latency_sec=0,
            sql=None
        )


@app.get("/api/vehicle/{vehicle_id}", response_model=VehicleStatus)
async def get_vehicle_status(vehicle_id: str):
    """Get mock vehicle status for dashboard display"""
    import random
    vehicles = {
        "V-001": ("EV-Civic", 64.0),
        "V-002": ("EV-Accord", 82.0),
        "V-003": ("EV-CR-V", 78.5),
        "V-004": ("EV-Pilot", 95.0),
        "V-005": ("EV-Odyssey", 100.0),
    }
    if vehicle_id not in vehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    model, battery_kwh = vehicles[vehicle_id]
    battery_pct = random.uniform(40, 95)
    efficiency = random.uniform(0.14, 0.22)
    return VehicleStatus(
        vehicle_id=vehicle_id,
        model=model,
        battery_pct=round(battery_pct, 1),
        range_km=round(battery_kwh * (battery_pct / 100) / efficiency, 0),
        battery_temp_c=round(random.uniform(22, 38), 1),
        last_trip_km=round(random.uniform(5, 80), 1),
        efficiency_kwh_per_km=round(efficiency, 3),
    )


@app.get("/api/vehicles")
async def list_vehicles():
    return [
        {"vehicle_id": "V-001", "model": "EV-Civic", "year": 2024},
        {"vehicle_id": "V-002", "model": "EV-Accord", "year": 2024},
        {"vehicle_id": "V-003", "model": "EV-CR-V", "year": 2025},
        {"vehicle_id": "V-004", "model": "EV-Pilot", "year": 2025},
        {"vehicle_id": "V-005", "model": "EV-Odyssey", "year": 2025},
    ]


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "genie_space_id": GENIE_SPACE_ID or "NOT SET",
        "fmapi_model": FMAPI_MODEL,
    }


# --- Serve React Frontend ---
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def root():
    return FileResponse(str(static_dir / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
