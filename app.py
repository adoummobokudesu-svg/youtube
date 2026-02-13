import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import isodate

# --- 安全なAPIキーの設定 ---
API_KEY = st.secrets["YOUTUBE_API_KEY"]
youtube = build('youtube', 'v3', developerKey=API_KEY)

st.set_page_config(page_title="YouTubeリサーチくん", layout="wide")
st.title("🎥 YouTubeリサーチ専用サイト")

# --- サイドバー：フィルタ設定 ---
st.sidebar.header("検索フィルタ")
query = st.sidebar.text_input("検索キーワード", value="火災保険")
duration_type = st.sidebar.radio("動画の長さ", ["すべて", "ショート (1分以内)", "ロング (7分以上)"])
period = st.sidebar.selectbox("期間", ["全期間", "1ヶ月以内", "2ヶ月以内", "6ヶ月以内", "1年以内"])
target_level = st.sidebar.select_slider("エンゲージメント段階", options=["段階1", "段階2", "段階3", "段階4", "段階5"], value="段階3")

def get_published_after(period_str):
    if period_str == "全期間": return None
    days = {"1ヶ月以内": 30, "2ヶ月以内": 60, "6ヶ月以内": 180, "1年以内": 365}
    dt = datetime.utcnow() - timedelta(days=days[period_str])
    return dt.isoformat() + "Z"

def get_level(ratio):
    if ratio >= 3.0: return "段階5"
    if ratio >= 1.5: return "段階4"
    if ratio >= 0.8: return "段階3"
    if ratio >= 0.4: return "段階2"
    return "段階1"

if st.sidebar.button("リサーチ開始"):
    published_after = get_published_after(period)
    search_res = youtube.search().list(
        q=query, part="snippet", maxResults=20, type="video", 
        publishedAfter=published_after, order="relevance"
    ).execute()

    video_ids = [item['id']['videoId'] for item in search_res['items']]
    
    if not video_ids:
        st.warning("動画が見つかりませんでした。")
    else:
        v_res = youtube.videos().list(id=','.join(video_ids), part="statistics,contentDetails,snippet").execute()
        
        for v in v_res['items']:
            seconds = isodate.parse_duration(v['contentDetails']['duration']).total_seconds()
            if duration_type == "ショート (1分以内)" and seconds > 60: continue
            if duration_type == "ロング (7分以上)" and seconds < 420: continue
            
            c_res = youtube.channels().list(id=v['snippet']['channelId'], part="statistics").execute()
            subs = int(c_res['items'][0]['statistics'].get('subscriberCount', 1))
            views = int(v['statistics'].get('viewCount', 0))
            
            ratio = views / subs if subs > 0 else 0
            current_level = get_level(ratio)
            
            if current_level == target_level:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(v['snippet']['thumbnails']['high']['url'])
                with col2:
                    st.subheader(v['snippet']['title'])
                    st.write(f"📺 **再生回数:** {views:,} 回 / 👤 **登録者数:** {subs:,} 人")
                    st.write(f"📈 **段階:** {current_level} (比率: {ratio:.2f})")
                    st.write(f"📝 **説明:** {v['snippet']['description'][:200]}...")
                    st.markdown(f"[動画を見る](https://www.youtube.com/watch?v={v['id']})")
                st.divider()
