import streamlit as st
import requests
import pandas as pd
import time
import os


API_BASE_URL = os.getenv("API_BASE_URL", "http://nginx:80/api/v1")

st.set_page_config(
    page_title="RAG Admin",
    page_icon="🧠",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
}
.stButton button {
    border-radius: 8px;
    background: #111827;
    color: white;
    border: none;
}
.stButton button:hover {
    background: #1f2937;
}
</style>
""", unsafe_allow_html=True)


def api_get(path):
    return requests.get(f"{API_BASE_URL}{path}", timeout=5)


def api_post(path, **kwargs):
    return requests.post(f"{API_BASE_URL}{path}", timeout=15, **kwargs)


def api_delete(path):
    return requests.delete(f"{API_BASE_URL}{path}", timeout=5)


st.title("RAG Admin Panel")
st.caption("Monitoring + управление системой")

with st.sidebar:
    st.subheader("🔌 API Status")

    try:
        base_url = API_BASE_URL.replace("/api/v1", "")
        r = requests.get(f"{base_url}/health", timeout=2)
        if r and r.status_code == 200:
            st.success("API OK")
            st.caption(f"mode: {r.json().get('mode')}")
        else:
            st.error("API error")
    except:
        st.error("API offline")


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📁 Collections",
    "📤 Index",
    "💬 Ask",
    "📊 Tasks",
    "📈 Metrics"
])

with tab1:
    st.subheader("Коллекции")

    col1, col2 = st.columns([2, 1])

    with col1:
        try:
            r = api_get("/qdrant/collections")
            data = r.json().get("collections", [])

            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Нет коллекций")
        except:
            st.error("Ошибка загрузки")

    with col2:
        st.markdown("### ➕ Создать")

        name = st.text_input("Name")
        size = st.selectbox("Vector size", [384, 768, 1024])
        distance = st.selectbox("Metric", ["Cosine", "Dot", "Euclidean"])

        if st.button("Create"):
            r = api_post(
                f"/qdrant/collections/{name}",
                params={"vector_size": size, "distance": distance}
            )
            if r.status_code == 200:
                st.success("Создано")
                st.rerun()
            else:
                st.error(r.text)

    st.divider()

    if 'data' in locals() and data:
        names = [c["name"] for c in data]

        col1, col2 = st.columns([3,1])
        with col1:
            delete_name = st.selectbox("Удалить коллекцию", names)
        with col2:
            if st.button("🗑️"):
                r = api_delete(f"/qdrant/collections/{delete_name}")
                if r.status_code == 200:
                    st.success("Удалено")
                    st.rerun()

with tab2:
    st.subheader("Индексация")

    mode = st.radio("Тип", ["JSON", "Pickle"], horizontal=True)

    col1, col2 = st.columns(2)

    with col1:
        collection = st.text_input("Collection")
        file = st.file_uploader("File", type=["json", "pkl"])

    with col2:
        recreate = st.checkbox("Recreate", True)
        batch = st.number_input("Batch size", value=100, min_value=1)

        if mode == "Pickle":
            vector_size = st.selectbox("Vector size", [384, 768, 1024, 1536])
            distance = st.selectbox("Distance", ["Cosine", "Euclidean", "Dot"])

    if st.button("Start"):
        if not file or not collection:
            st.warning("Заполните все поля")
        else:
            try:
                if mode == "JSON":
                    endpoint = "/index/index"
                    files = {"file": (file.name, file.getvalue(), "application/json")}
                    data = {
                        "collection_name": collection,
                        "force_recreate": str(recreate).lower(),
                        "batch_size": batch
                    }
                else:
                    endpoint = "/index/upload"
                    files = {"pickle_file": (file.name, file.getvalue(), "application/octet-stream")}
                    data = {
                        "collection": collection,
                        "vector_size": vector_size,
                        "distance": distance,
                        "batch_size": batch,
                        "force_recreate": str(recreate).lower()
                    }

                r = api_post(endpoint, files=files, data=data)

                if r and r.status_code == 200:
                    res = r.json()
                    st.success("Задача запущена")
                    st.code(f"Task ID: {res.get('task_id')}")
                    st.info(f"Коллекция: {collection}")
                else:
                    st.error(f"Ошибка: {r.status_code if r else 'No response'}")
                    if r and r.text:
                        st.text(r.text[:500])

            except Exception as e:
                st.error(f"Ошибка: {e}")

with tab3:
    st.subheader("RAG запрос")

    question = st.text_area("Вопрос")
    style = st.selectbox("Стиль", ["concise", "detailed"])

    if st.button("Ask"):
        r = api_post("/rag/ask", json={
            "question": question,
            "style": style
        })

        if r and r.status_code == 200:
            task_id = r.json().get("task_id")

            if not task_id:
                st.error("Не получен task_id")
            else:
                progress = st.progress(0)

                for i in range(60):
                    resp = api_get(f"/status/{task_id}")

                    if resp and resp.status_code == 200:
                        status = resp.json()

                        current_status = status.get("status")

                        if current_status == "completed":
                            progress.progress(100)
                            st.success("Готово")
                            st.markdown(status.get("result", {}).get("answer", ""))

                            metrics = status.get("result", {})
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Latency (s)", round(metrics.get("latency_sec", 0), 2))
                            col2.metric("Cached", str(metrics.get("cached", False)))
                            break

                        elif current_status == "failed":
                            st.error(status.get("error"))
                            break

                        elif current_status in ["pending", "processing"]:
                            progress.progress(min(i * 2, 90))
                            time.sleep(1)
                        else:
                            time.sleep(1)
                    else:
                        time.sleep(1)

with tab4:
    st.subheader("Задачи")

    try:
        r = api_get("/status/")
        tasks = r.json()

        if tasks:
            df = pd.DataFrame(tasks)

            columns_to_drop = ["task_type", "collection_name", "started_at", "created_at", "progress"]
            columns_to_drop_existing = [col for col in columns_to_drop if col in df.columns]

            df = df.drop(columns=columns_to_drop_existing)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Нет задач")
    except:
        st.error("Ошибка загрузки")

with tab5:
    st.subheader("Monitoring")

    if st.button("Обновить метрики"):
        try:
            r_metrics = api_get("/status/metrics")

            if r_metrics and r_metrics.status_code == 200:
                data = r_metrics.json()

                if "error" not in data:
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Requests", data.get("total_requests", 0))
                    col2.metric("Avg latency (sec)", data.get("avg_latency", 0))
                    col3.metric("Cache hit %", f"{data.get('cache_hit_rate', 0) * 100:.1f}%")
                    col4.metric("Cache hits", data.get("cache_hits", 0))

                    st.divider()

                    st.subheader("📊 Cache статистика")
                    st.bar_chart({
                        "Hits": [data.get("cache_hits", 0)],
                        "Misses": [data.get("cache_misses", 0)]
                    })
                else:
                    st.error(f"Ошибка: {data['error']}")
            else:
                st.error(f"Ошибка загрузки метрик: {r_metrics.status_code if r_metrics else 'No response'}")

            st.divider()

            st.subheader("Queue статистика")

            r_queue = api_get("/status/queue/stats")

            if r_queue and r_queue.status_code == 200:
                q_data = r_queue.json()

                c1, c2, c3 = st.columns(3)
                c1.metric("Queue size", q_data.get("queue_length", 0))
                c2.metric("Total tasks", q_data.get("total_tasks", 0))

                status_counts = q_data.get("status_counts", {})
                processing = status_counts.get("processing", 0)
                completed = status_counts.get("completed", 0)
                failed = status_counts.get("failed", 0)

                c3.metric("Processing", processing)

                if completed > 0 or failed > 0:
                    st.caption(f"Completed: {completed} | Failed: {failed}")
            else:
                st.error(f"Ошибка загрузки очереди: {r_queue.status_code if r_queue else 'No response'}")

        except Exception as e:
            st.error(f"Ошибка: {e}")