import sys
import os

file_path = r'c:\Users\USER\Desktop\BOT-SVSU\BOT_BACKEND\api_server.py'
with open(file_path, 'r') as f:
    lines = f.readlines()

# Find the start and end of the mess
start = -1
end = -1
for i, line in enumerate(lines):
    if '@app.get("/api/applications")' in line:
        start = i
    if '@app.post("/api/voice-text")' in line:
        end = i
        break

if start != -1 and end != -1:
    new_content = """@app.get("/api/applications")
async def get_applications():
    try:
        df = load_applications_df()
        if not df.empty:
            df['dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = df.sort_values(by='dt', ascending=False, na_position='last').drop(columns=['dt'])
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error reading applications: {e}")
        return []

@app.get("/api/dashboard-stats")
async def get_dashboard_stats():
    from datetime import datetime, timedelta
    try:
        now = datetime.now()
        stats = {
            "total_leads": 0,
            "total_apps": 0,
            "total_traffic": 0,
            "engagement": {
                "today": 0,
                "yesterday": 0,
                "this_month": 0
            },
            "traffic": {
                "today": 0,
                "yesterday": 0,
                "this_month": 0
            },
            "bot_distribution": {
                "intelligent": 0,
                "general": 0,
                "admission": 0
            },
            "daily_trend": {
                "labels": [],
                "data": []
            },
            "top_courses": [],
            "top_cities": []
        }
        
        df_leads = load_leads_df()
        stats["total_leads"] = len(df_leads)

        df_engagement = load_engagements_df()
        if df_engagement.empty and not df_leads.empty:
            df_engagement = pd.DataFrame({
                "lead_id": df_leads["lead_id"],
                "email": df_leads["email"],
                "mobile": df_leads["mobile"],
                "bot_type": df_leads["bot_type"],
                "purpose": df_leads["purpose"],
                "timestamp": df_leads["created_at"].where(df_leads["created_at"] != "", df_leads["timestamp"])
            })

        if not df_engagement.empty:
            df_engagement["engagement_dt"] = pd.to_datetime(df_engagement["timestamp"], errors="coerce")
            df_engagement = df_engagement.dropna(subset=["engagement_dt"]).copy()
            if not df_engagement.empty:
                df_engagement["identity_key"] = df_engagement.apply(get_engagement_identity_key, axis=1)

                today_mask = df_engagement["engagement_dt"].dt.date == now.date()
                yesterday_mask = df_engagement["engagement_dt"].dt.date == (now - timedelta(days=1)).date()
                month_mask = df_engagement["engagement_dt"].dt.month == now.month

                stats["engagement"]["today"] = int(df_engagement.loc[today_mask, "identity_key"].nunique())
                stats["engagement"]["yesterday"] = int(df_engagement.loc[yesterday_mask, "identity_key"].nunique())
                stats["engagement"]["this_month"] = int(df_engagement.loc[month_mask, "identity_key"].nunique())

                labels = []
                counts = []
                for i in range(6, -1, -1):
                    day = (now - timedelta(days=i)).date()
                    labels.append((now - timedelta(days=i)).strftime("%a"))
                    counts.append(int(df_engagement.loc[df_engagement["engagement_dt"].dt.date == day, "identity_key"].nunique()))

                if sum(counts) == 0:
                    active_daily = (
                        df_engagement.assign(day=df_engagement["engagement_dt"].dt.date)
                        .groupby("day")["identity_key"]
                        .nunique()
                        .reset_index(name="count")
                        .sort_values("day")
                    )
                    if not active_daily.empty:
                        active_daily = active_daily.tail(7)
                        labels = [pd.to_datetime(day).strftime("%b %d") for day in active_daily["day"]]
                        counts = [int(v) for v in active_daily["count"]]

                stats["daily_trend"]["labels"] = labels
                stats["daily_trend"]["data"] = counts

        traffic_available = False
        if os.path.exists(TRAFFIC_FILE):
            try:
                df_t = deduplicate_traffic_df(load_traffic_df())
                if not df_t.empty:
                    traffic_available = True
                    df_t['dt'] = pd.to_datetime(df_t['timestamp'], errors='coerce')
                    df_t = df_t.dropna(subset=['dt']).copy()
                    stats["total_traffic"] = len(df_t)
                    stats["traffic"]["today"] = int(len(df_t[df_t['dt'].dt.date == now.date()]))
                    stats["traffic"]["yesterday"] = int(len(df_t[df_t['dt'].dt.date == (now - timedelta(days=1)).date()]))
                    stats["traffic"]["this_month"] = int(len(df_t[df_t['dt'].dt.month == now.month]))

                    if 'bot_type' in df_t.columns:
                        t_dist = df_t['bot_type'].astype(str).str.lower().value_counts().to_dict()
                        for k, v in t_dist.items():
                            if k in stats["bot_distribution"]:
                                stats["bot_distribution"][k] = int(v)
            except Exception as traffic_stats_err:
                print(f"Traffic Stats Parse Error: {traffic_stats_err}")

        if not traffic_available:
            stats["total_traffic"] = stats["total_leads"]
            if not df_leads.empty:
                if 'bot_type' in df_leads.columns:
                    dist = df_leads['bot_type'].astype(str).lower().value_counts().to_dict()
                    for k, v in dist.items():
                        if k in stats["bot_distribution"]:
                            stats["bot_distribution"][k] = int(v)
                else:
                    stats["bot_distribution"]["intelligent"] = len(df_leads)
            
    except Exception as e:
        import traceback
        print(f"Stats Processing Error: {e}\\n{traceback.format_exc()}")
        if "total_traffic" not in stats: stats["total_traffic"] = stats.get("total_leads", 0)
            
    try:
        df_apps = load_applications_df()
        stats["total_apps"] = len(df_apps)
        if not df_apps.empty:
            if 'course' in df_apps.columns:
                course_counts = df_apps['course'].value_counts().head(5).to_dict()
                stats["top_courses"] = [{"course": k, "count": int(v)} for k, v in course_counts.items()]
            if 'city' in df_apps.columns:
                city_counts = df_apps['city'].value_counts().head(8).to_dict()
                stats["top_cities"] = [{"city": k, "count": int(v)} for k, v in city_counts.items()]
    except Exception as e:
        print(f"Stats Error Apps: {e}")
            
    return stats

@app.post("/api/voice")
async def voice_chat(audio_file: UploadFile = File(...), history: str = ""):
    import json
    conversation_history = json.loads(history) if history else []
    import edge_tts
    client = get_groq_client()
    if not client: raise HTTPException(status_code=503, detail="Groq API not configured")
    try:
        file_id = str(uuid.uuid4())
        input_path = f"temp_audio/{file_id}.webm"
        content = await audio_file.read()
        with open(input_path, "wb") as f: f.write(content)
        with open(input_path, "rb") as fileData:
            transcription = client.audio.transcriptions.create(
                file=(input_path, fileData.read()),
                model="whisper-large-v3-turbo", 
                response_format="json",
                temperature=0.0
            )
        user_text = transcription.text.strip()
        if not user_text or len(user_text) < 2:
            return {"transcription": "", "response": "Ji, main sun rahi hoon. Kripya punah prayaas karein.", "audio": ""}
        result = await generate_voice_response(user_text, conversation_history, file_id)
        if os.path.exists(input_path): os.remove(input_path)
        return result
    except Exception as e:
        print(f"Voice Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
    lines[start:end] = [new_content + "\\n"]
    with open(file_path, 'w') as f:
        f.writelines(lines)
    print("Repair successful")
else:
    print(f"Failed to find markers: start={start}, end={end}")
