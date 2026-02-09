import streamlit as st
import sqlite3
import os
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from streamlit_calendar import calendar

# ───────────────────────────────
# 1. メール送信設定
# ───────────────────────────────
SENDER_EMAIL = "o.oneonceover@gmail.com"
SENDER_PASS = "ここに16桁のアプリパスワードを入力"

# ───────────────────────────────
# 2. 基本設定・祝日データ
# ───────────────────────────────
st.set_page_config(page_title="One Once Over", layout="wide")

HOLIDAY_MAP = {
    "2025-01-01": "元日", "2025-01-13": "成人の日", "2025-02-11": "建国記念の日", 
    "2025-02-23": "天皇誕生日", "2025-02-24": "振替休日", "2025-03-20": "春分の日",
    "2025-04-29": "昭和の日", "2025-05-03": "憲法記念日", "2025-05-04": "みどりの日", 
    "2025-05-05": "こどもの日", "2025-05-06": "振替休日", "2025-07-21": "海の日",
    "2025-08-11": "山の日", "2025-09-15": "敬老の日", "2025-09-23": "秋分の日", 
    "2025-10-13": "スポーツの日", "2025-11-03": "文化の日", "2025-11-23": "勤労感謝の日", 
    "2025-11-24": "振替休日",
    "2026-01-01": "元日", "2026-01-12": "成人の日", "2026-02-11": "建国記念の日", 
    "2026-02-23": "天皇誕生日", "2026-03-20": "春分の日", "2026-04-29": "昭和の日",
    "2026-05-03": "憲法記念日", "2026-05-04": "みどりの日", "2026-05-05": "こどもの日", 
    "2026-05-06": "振替休日", "2026-07-20": "海の日", "2026-08-11": "山の日",
    "2026-09-21": "敬老の日", "2026-09-22": "国民の休日", "2026-09-23": "秋分の日", 
    "2026-10-12": "スポーツの日", "2026-11-03": "文化の日", "2026-11-23": "勤労感謝の日"
}

# ───────────────────────────────
# 3. データベース準備
# ───────────────────────────────
conn = sqlite3.connect('live_reservation.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS site_info (key TEXT PRIMARY KEY, value TEXT)')
c.execute('''CREATE TABLE IF NOT EXISTS events 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, title TEXT, description TEXT, 
              open_time TEXT, start_time TEXT, price TEXT, location TEXT, 
              image_path TEXT, image_path2 TEXT)''')
c.execute('CREATE TABLE IF NOT EXISTS reservations (id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER, name TEXT, people INTEGER, email TEXT)')
conn.commit()

def get_info(key, default=""):
    c.execute("SELECT value FROM site_info WHERE key=?", (key,))
    res = c.fetchone()
    return res[0] if res else default

def save_info(key, value):
    c.execute("INSERT OR REPLACE INTO site_info (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()

def send_mail(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        st.error(f"メール送信エラー: {e}")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'page' not in st.session_state: st.session_state.page = "top"
if 'selected_date' not in st.session_state: st.session_state.selected_date = None

# ───────────────────────────────
# 4. デザイン設定の読み込みと反映
# ───────────────────────────────
bg_color = get_info("bg_color", "#0e1117")
text_color = get_info("text_color", "#ffffff")
font_family = get_info("font_family", "sans-serif")
font_size = get_info("font_size", "16")
event_color = get_info("event_color", "#3788d8")
border_color = get_info("border_color", "#444444")
bg_img_base64 = get_info("bg_image", "")

bg_style = f"background-image: url('data:image/png;base64,{bg_img_base64}');" if bg_img_base64 else f"background-color: {bg_color};"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP&family=M+PLUS+Rounded+1c&family=Sawarabi+Mincho&display=swap');
    .stApp {{ 
        {bg_style} background-attachment: fixed; background-size: cover;
        color: {text_color}; font-family: {font_family}; font-size: {font_size}px;
    }}
    h1, h2, h3, p, span, label, div {{ color: {text_color} !important; }}
    /* カレンダー色分け */
    .fc-day-sat .fc-daygrid-day-number {{ color: #00ccff !important; }}
    .fc-day-sun .fc-daygrid-day-number {{ color: #ff4500 !important; }}
    .holiday-marker {{ background-color: rgba(255, 69, 0, 0.05) !important; }}
    .holiday-marker::before {{ content: "●"; color: #ff4500; font-size: 8px; margin-right: 3px; }}
    .fc-daygrid-day {{ border: 1px solid {border_color} !important; }}
    </style>
    """, unsafe_allow_html=True)

# ───────────────────────────────
# 5. メインロジック
# ───────────────────────────────
if st.session_state.page == "top":
    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.title(get_info("title", "One Once Over"))
    with col_btn:
        if st.button("📅 ライブ予定一覧"):
            st.session_state.page = "list"; st.rerun()

    # --- サイドバー：オーナー設定 ---
    with st.sidebar:
        if not st.session_state.logged_in:
            pw = st.text_input("Owner Password", type="password")
            if st.button("Login"):
                if pw == "owner123": st.session_state.logged_in = True; st.rerun()
        else:
            if st.button("Logout"): st.session_state.logged_in = False; st.rerun()
            st.divider()
            st.subheader("🎨 デザイン詳細設定")
            f_fam = st.selectbox("フォント", ["sans-serif", "'Noto Sans JP'", "'M PLUS Rounded 1c'", "'Sawarabi Mincho'"], index=0)
            f_size = st.slider("基本文字サイズ", 12, 24, int(font_size))
            b_col = st.color_picker("背景色", bg_color)
            t_col = st.color_picker("文字色", text_color)
            e_col = st.color_picker("カレンダーイベント色", event_color)
            bd_col = st.color_picker("カレンダー枠線色", border_color)
            bg_file = st.file_uploader("背景画像アップロード", type=['jpg','png'])
            if st.button("デザインを保存"):
                save_info("font_family", f_fam); save_info("font_size", f_size)
                save_info("bg_color", b_col); save_info("text_color", t_col)
                save_info("event_color", e_col); save_info("border_color", bd_col)
                if bg_file: save_info("bg_image", base64.b64encode(bg_file.read()).decode())
                st.rerun()

    # TOP画像と紹介文
    top_img_path = get_info("top_image")
    if top_img_path and os.path.exists(top_img_path):
        st.image(top_img_path, use_container_width=True)
    st.markdown(get_info("description", "Welcome to One Once Over"))
    sns = get_info("sns_link")
    if sns: st.markdown(f"[SNS Link]({sns})")

    # --- カレンダー準備 ---
    cal_events = []
    # 祝日
    for d_str, name in HOLIDAY_MAP.items():
        cal_events.append({"title": f"🚩{name}", "start": d_str, "display": "block", "backgroundColor": "transparent", "borderColor": "transparent", "textColor": "#ff4500", "classNames": ["holiday-marker"]})
    # ライブ
    c.execute("SELECT date, title, image_path FROM events")
    for row in c.fetchall():
        icon = "📸 " if row[2] else "🎸 "
        cal_events.append({"title": f"{icon}{row[1]}", "start": row[0], "backgroundColor": event_color, "borderColor": event_color, "textColor": "#ffffff"})

    state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "firstDay": 1}, key="main_cal")

    # クリック遷移
    if state and "eventClick" in state:
        raw_t = state["eventClick"]["event"].get("title", "")
        if "🚩" not in raw_t:
            clean_t = raw_t.replace("📸 ", "").replace("🎸 ", "")
            c.execute("SELECT date FROM events WHERE title=?", (clean_t,))
            res = c.fetchone()
            if res: st.session_state.selected_date = res[0]; st.session_state.page = "detail"; st.rerun()

    # --- 管理メニュー ---
    if st.session_state.logged_in:
        with st.expander("🛠 管理メニュー", expanded=True):
            t1, t2, t3 = st.tabs(["サイト情報", "ライブ登録", "削除"])
            with t1:
                e_title = st.text_input("サイト名", value=get_info("title"))
                e_desc = st.text_area("紹介文", value=get_info("description"))
                e_sns = st.text_input("SNSリンク", value=get_info("sns_link"))
                uploaded_top = st.file_uploader("TOP画像アップロード", type=['jpg','png','jpeg'])
                if st.button("サイト情報を更新"):
                    save_info("title", e_title); save_info("description", e_desc); save_info("sns_link", e_sns)
                    if uploaded_top:
                        with open("top_img.jpg", "wb") as f: f.write(uploaded_top.getbuffer())
                        save_info("top_image", "top_img.jpg")
                    st.rerun()
            with t2:
                with st.form("add_live"):
                    d = st.date_input("開催日"); t = st.text_input("ライブ名")
                    op = st.text_input("OPEN時間"); stt = st.text_input(" 出演時間")
                    pr = st.text_input("料金"); loc = st.text_input("会場住所")
                    desc = st.text_area("詳細説明")
                    img1 = st.file_uploader("カレンダー用画像", type=['jpg','png'])
                    if st.form_submit_button("ライブを公開する"):
                        p1 = f"img1_{d}_{t}.jpg" if img1 else ""
                        if img1: 
                            with open(p1, "wb") as f: f.write(img1.getbuffer())
                        c.execute("INSERT INTO events (date, title, description, open_time, start_time, price, location, image_path) VALUES (?,?,?,?,?,?,?,?)", (d.strftime("%Y-%m-%d"), t, desc, op, stt, pr, loc, p1))
                        conn.commit(); st.rerun()
            with t3:
                c.execute("SELECT id, date, title FROM events ORDER BY date DESC")
                for ev_id, ev_date, ev_title in c.fetchall():
                    if st.button(f"🗑 {ev_date} {ev_title} を削除", key=f"del_{ev_id}"):
                        c.execute("DELETE FROM events WHERE id=?", (ev_id,)); conn.commit(); st.rerun()

# --- 詳細・リストページ ---
elif st.session_state.page == "list":
    st.button("← 戻る", on_click=lambda: setattr(st.session_state, 'page', 'top'))
    c.execute("SELECT date, title, image_path FROM events ORDER BY date ASC")
    for row in c.fetchall():
        with st.container(border=True):
            col_i, col_t = st.columns([1, 4])
            if row[2] and os.path.exists(row[2]): col_i.image(row[2], width=100)
            col_t.subheader(f"{row[0]} : {row[1]}")
            if st.button("詳細へ", key=f"btn_{row[0]}"):
                st.session_state.selected_date = row[0]; st.session_state.page = "detail"; st.rerun()

elif st.session_state.page == "detail":
    date = st.session_state.selected_date
    st.button("← カレンダーへ戻る", on_click=lambda: setattr(st.session_state, 'page', 'top'))
    c.execute("SELECT id, title, description, open_time, start_time, price, location, image_path FROM events WHERE date=?", (date,))
    ev = c.fetchone()
    if ev:
        ev_id, title, description, op, stt, pr, loc, p1 = ev
        st.header(title)
        st.write(f"📅 {date} | 開場: {op} / 出演時間: {stt} | 🎫: {pr}")
        if p1 and os.path.exists(p1): st.image(p1, width=500)
        st.write(description)
        if st.session_state.logged_in:
            st.divider(); st.subheader("👥 予約者リスト")
            c.execute("SELECT name, people, email FROM reservations WHERE event_id=?", (ev_id,))
            for r in c.fetchall(): st.write(f"・{r[0]}様 {r[1]}名 ({r[2]})")
        else:
            with st.form("res_form"):
                n = st.text_input("お名前"); p = st.number_input("人数", 1); m = st.text_input("メールアドレス")
                if st.form_submit_button("予約を確定する"):
                    c.execute("INSERT INTO reservations (event_id, name, people, email) VALUES (?,?,?,?)", (ev_id, n, p, m))
                    conn.commit()
                    body = f"新規予約が入りました！\nライブ: {title}\nお名前: {n}様\n人数: {p}名\nメール: {m}"
                    send_mail(SENDER_EMAIL, f"【予約通知】{title}", body)
                    st.balloons(); st.success("ご予約完了いたしました！"); st.rerun()
