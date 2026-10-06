import time
import requests
import streamlit as st

# 請替換成你在 Render 部署的後端 API 網址
RENDER_API_URL = "https://one006-blockchain-backend.onrender.com"
ROOT_TOKEN_AUTH = "Bearer root_super_secret_password_change_me"

st.set_page_config(layout="wide", page_title="遠端區塊鏈監控中心 [已上鎖]")

# 透過 JavaScript 徹底清除並禁絕瀏覽器的「已儲存資訊」快顯與自動填入
st.markdown("""
<script>
const disableAutofill = () => {
    const inputs = window.parent.document.querySelectorAll('input');
    inputs.forEach(input => {
        input.setAttribute('autocomplete', 'off');
        input.setAttribute('autocorrect', 'off');
        input.setAttribute('autocapitalize', 'off');
        input.setAttribute('spellcheck', 'false');
        input.setAttribute('data-form-type', 'other');
    });
};
setTimeout(disableAutofill, 500);
setInterval(disableAutofill, 1000);
</script>
""", unsafe_allow_html=True)

# 初始化 Session State
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "current_user" not in st.session_state:
    st.session_state["current_user"] = None

# 登入驗證介面
if not st.session_state["authenticated"]:
    st.markdown("<h2 style='text-align: center;'>🔐 遠端區塊鏈與 IPFS 節點監控中心</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.info("⚠️ 此系統已受保護，請輸入帳號與密碼以解鎖檢視。")
        input_user = st.text_input("帳號 (Username)", key="login_user")
        input_pass = st.text_input("密碼 (Password)", type="password", key="login_pass")

        if st.button("登入系統", use_container_width=True, type="primary"):
            try:
                res = requests.post(f"{RENDER_API_URL}/api/login", json={
                    "username": input_user,
                    "password": input_pass
                }, timeout=10)
                
                if res.status_code == 200:
                    st.session_state["authenticated"] = True
                    st.session_state["current_user"] = input_user
                    st.success(f"歡迎回來，{input_user}！登入成功。")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ 帳號或密碼錯誤，請重新輸入！")
            except Exception as e:
                st.error(f"無法連線至後端伺服器，請稍後再試：{e}")
    st.stop()

# --- 通過驗證後的管理與監控主畫面 ---
st.title("🔒 遠端區塊鏈與 IPFS 節點監控中心 (Root Protected)")

col1, col2 = st.columns([4, 1])
with col1:
    st.success(f"🔓 系統已解鎖：目前登入帳戶為 `{st.session_state['current_user']}`，正在透過 Render 節點監控區塊鏈。")
with col2:
    if st.button("🔒 登出系統", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["current_user"] = None
        st.rerun()

if st.button("🔄 即時刷新數據", use_container_width=True):
    st.rerun()

auto_refresh = st.checkbox("⏱ 啟用 30 秒自動刷新", value=True)

# 向 Render 後端抓取數據
headers = {"Authorization": ROOT_TOKEN_AUTH}
try:
    ledger_res = requests.get(f"{RENDER_API_URL}/api/get_ledger", headers=headers, timeout=10)
    ledger_data = ledger_res.json() if ledger_res.status_code == 200 else []

    stats_res = requests.get(f"{RENDER_API_URL}/api/get_stats", headers=headers, timeout=10)
    stats = stats_res.json() if stats_res.status_code == 200 else {"ledger_len": 0, "ipfs_count": 0, "keys_count": 0}
except Exception as e:
    st.error(f"連線至後端 API 失敗: {e}")
    ledger_data = []
    stats = {"ledger_len": 0, "ipfs_count": 0, "keys_count": 0}

m1, m2, m3 = st.columns(3)
m1.metric("📦 區塊鏈當前高度 (Blocks)", stats["ledger_len"])
m2.metric("🗂️ IPFS 儲存節點檔案數", stats["ipfs_count"])
m3.metric("🔑 已註冊使用者公鑰數", stats["keys_count"])

st.markdown("---")
st.subheader("📜 區塊鏈帳本即時狀態")

if ledger_data:
    markdown_table = [
        "| 高度 | 時間戳記 | 簽章帳戶 | 影像 ID | IPFS CID | Merkle Root 密文 (節錄) | 數位簽章 (節錄) |",
        "| :---: | :---: | :---: | :---: | :---: | :--- | :--- |"
    ]
    
    for block in reversed(ledger_data):
        height = block.get("block_height", "-")
        ts = block.get("timestamp", "-")
        signer = block.get("signer_user", "-")
        img_id = block.get("image_id", "-")
        cid = block.get("ipfs_cid", "-")
        
        enc_root = str(block.get("merkle_root_ciphertext", "-"))
        enc_root_short = f"`{enc_root[:16]}...`" if len(enc_root) > 16 else f"`{enc_root}`"
        
        sig = str(block.get("digital_signature_hex", "-"))
        sig_short = f"`{sig[:16]}...`" if len(sig) > 16 else f"`{sig}`"
        
        markdown_table.append(f"| {height} | {ts} | {signer} | {img_id} | {cid} | {enc_root_short} | {sig_short} |")
    
    st.markdown("\n".join(markdown_table))
else:
    st.warning("目前區塊鏈帳本中尚無任何區塊紀錄或無法取得資料。")

st.markdown("---")
st.subheader("⚠️ 節點管理危險操作")
if st.button("🚨 清空伺服器所有區塊鏈與 IPFS 數據", type="primary"):
    try:
        clear_res = requests.post(f"{RENDER_API_URL}/api/clear_data", headers=headers, timeout=10)
        if clear_res.status_code == 200:
            st.success("伺服器資料已完全清空重置。")
            time.sleep(1)
            st.rerun()
        else:
            st.error("清空失敗，權限不足或伺服器錯誤。")
    except Exception as e:
        st.error(f"無法連線至後端執行清空動作: {e}")

if auto_refresh:
    time.sleep(30)
    st.rerun()