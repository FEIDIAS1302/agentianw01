import streamlit as st
import google.generativeai as genai
import json
import re
import zipfile
import io
import datetime
from PyPDF2 import PdfReader
from pptx import Presentation

# --- 設定 ---
# ※APIキーはSecrets管理推奨
genai.configure(api_key="YOUR_GEMINI_API_KEY")

st.set_page_config(page_title="動画制作オーダーシステム", layout="centered")

# --- データ定義 (ここを実際のファイルパスに書き換えます) ---

# 背景データの定義
BACKGROUNDS = {
    "bg_01": {"name": "オフィス (Blue)", "img_url": "https://placehold.co/600x337/007bff/ffffff?text=Office+Blue"},
    "bg_02": {"name": "オフィス (Bright)", "img_url": "https://placehold.co/600x337/ffc107/ffffff?text=Office+Bright"},
    "bg_03": {"name": "テック (Abstract)", "img_url": "https://placehold.co/600x337/6610f2/ffffff?text=Tech+Abstract"},
    "bg_04": {"name": "シンプル (White)", "img_url": "https://placehold.co/600x337/f8f9fa/000000?text=Simple+White"},
}

# BGMデータの定義
# ※実際のファイルがあるパスを指定してください (例: "assets/bgm_up.mp3")
# ※テスト用にダミーパスを入れていますが、ファイルがない場合は警告が出ます
BGMS = {
    "bgm_01": {"name": "信頼・明るい", "file": "assets/bgm_corporate.mp3", "desc": "企業の信頼感を強調する王道サウンド"},
    "bgm_02": {"name": "誠実・穏やか", "file": "assets/bgm_calm.mp3", "desc": "落ち着いた説明向けのピアノ曲"},
    "bgm_03": {"name": "先進的・クール", "file": "assets/bgm_tech.mp3", "desc": "IT系に合うデジタルなビート"},
    "bgm_04": {"name": "エネルギッシュ", "file": "assets/bgm_energy.mp3", "desc": "勢いのあるモチベーションUP系"},
}

# アバターデータの定義
AVATARS = {
    "avatar_a": "👩 女性（スーツ）",
    "avatar_b": "👨 男性（スーツ）",
    "avatar_c": "👩 女性（カジュアル）"
}

# --- 関数群 ---

def sanitize_filename(name):
    """ファイル名に使えない文字を削除"""
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', name)
    return clean_name if clean_name else "Client"

def extract_text_from_file(uploaded_file):
    """PDF/PPTXからテキスト抽出"""
    text = ""
    file_ext = uploaded_file.name.split('.')[-1].lower()
    try:
        if file_ext == 'pdf':
            pdf_reader = PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        elif file_ext in ['pptx', 'ppt']:
            prs = Presentation(uploaded_file)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
    return text

def generate_script_with_gemini(raw_text):
    """Geminiによる台本生成"""
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    prompt = f"""
    あなたはプロの映像構成作家です。
    以下の会社資料のテキストから、会社説明動画用のナレーション台本を作成してください。
    
    【条件】
    - 文字数：読んだときに1500文字前後
    - 構成：導入(共感) -> 概要 -> 強み -> 結び
    - 出力形式：台本テキストのみ（注釈不要）
    
    【資料テキスト】
    {raw_text[:30000]} 
    """
    response = model.generate_content(prompt)
    return response.text

# --- UI構築 ---

st.title("📹 動画制作オーダーフォーム")
st.markdown("以下のステップに従って、動画の仕様を決定してください。")

# 1. 会社情報
with st.container():
    st.header("1. 基本情報")
    col1, col2 = st.columns(2)
    with col1:
        company_name_input = st.text_input("会社名 (アルファベット)", placeholder="Ex: NuWorks")
    with col2:
        today_str = datetime.date.today().strftime('%Y%m%d')
        st.text_input("発注日", value=today_str, disabled=True)

    logo_file = st.file_uploader("会社ロゴ (透過PNG)", type=["png"])
    if logo_file:
        st.image(logo_file, width=100)

st.divider()

# 2. デザイン選択 (プレビュー付き)
st.header("2. デザイン・演出")

# --- 背景選択セクション ---
st.subheader("🖼 背景スタイルを選択")
st.caption("以下の4パターンから選択してください")

# 4列のカラムを作成
bg_cols = st.columns(4)
bg_keys = list(BACKGROUNDS.keys())

# 画像を並べる
for i, key in enumerate(bg_keys):
    with bg_cols[i]:
        st.image(BACKGROUNDS[key]["img_url"], use_column_width=True)
        st.caption(f"No.{i+1}: {BACKGROUNDS[key]['name']}")

# ラジオボタンで選択
selected_bg_key = st.radio(
    "使用する背景:",
    bg_keys,
    format_func=lambda x: f"No.{bg_keys.index(x)+1}: {BACKGROUNDS[x]['name']}",
    horizontal=True
)

st.divider()

# --- BGM選択セクション ---
st.subheader("🎵 BGMを選択")
st.caption("再生ボタンを押して試聴できます")

bgm_keys = list(BGMS.keys())

# 2列x2行のようなグリッドにするか、リストにするか。今回はリスト形式で見やすくします。
for key in bgm_keys:
    col_play, col_desc = st.columns([1, 2])
    with col_play:
        st.markdown(f"**{BGMS[key]['name']}**")
        # 実際にファイルがあれば再生プレイヤーを表示
        # ※ファイルがない場合はプレースホルダーメッセージを表示
        try:
            st.audio(BGMS[key]["file"])
        except:
            st.warning(f"サンプル音源が見つかりません: {BGMS[key]['file']}")
    with col_desc:
        st.write(BGMS[key]["desc"])

selected_bgm_key = st.radio(
    "使用するBGM:",
    bgm_keys,
    format_func=lambda x: BGMS[x]['name'],
    horizontal=True
)

st.divider()

# --- アバター選択 ---
st.subheader("👤 アバターを選択")
selected_avatar_key = st.selectbox(
    "出演させるアバター:",
    list(AVATARS.keys()),
    format_func=lambda x: AVATARS[x]
)

st.divider()

# 3. 資料アップロード
st.header("3. 資料読込・台本生成")
uploaded_doc = st.file_uploader("会社概要資料 (PDF/PPTX)", type=['pdf', 'pptx'])

if st.button("AI台本生成スタート", type="primary"):
    if not uploaded_doc:
        st.error("資料をアップロードしてください。")
    elif not company_name_input:
        st.error("会社名を入力してください。")
    else:
        with st.spinner("資料を分析し、台本を執筆中..."):
            doc_text = extract_text_from_file(uploaded_doc)
            if doc_text:
                script_text = generate_script_with_gemini(doc_text)
                st.session_state['generated_script'] = script_text
                st.success("台本が生成されました！")

# 4. 最終確認・送信
if 'generated_script' in st.session_state:
    st.divider()
    st.subheader("📝 最終確認")
    final_script = st.text_area("台本内容 (修正可能)", st.session_state['generated_script'], height=300)
    
    # 選択内容の確認表示
    st.info(f"""
    **選択された構成:**
    - 背景: {BACKGROUNDS[selected_bg_key]['name']}
    - BGM: {BGMS[selected_bgm_key]['name']}
    - アバター: {AVATARS[selected_avatar_key]}
    """)
    
    clean_company = sanitize_filename(company_name_input)
    base_filename = f"{clean_company}_{today_str}"
    
    if st.button("制作データを送信する"):
        if not logo_file:
            st.error("ロゴ画像が必須です！")
        else:
            # JSON作成
            order_data = {
                "company_name": company_name_input,
                "date": today_str,
                "background_id": selected_bg_key,  # bg_01 等
                "bgm_id": selected_bgm_key,        # bgm_01 等
                "avatar_id": selected_avatar_key,
                "script": final_script,
                "logo_filename": f"logo_{base_filename}.png"
            }
            json_str = json.dumps(order_data, ensure_ascii=False, indent=2)
            
            # ZIP作成
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr(f"{base_filename}_order.json", json_str)
                logo_file.seek(0)
                zip_file.writestr(f"logo_{base_filename}.png", logo_file.read())
            
            zip_buffer.seek(0)
            
            st.success(f"データセット '{base_filename}.zip' が作成されました！")
            st.download_button(
                label="📤 データをダウンロード (送付用)",
                data=zip_buffer,
                file_name=f"{base_filename}.zip",
                mime="application/zip"
            )