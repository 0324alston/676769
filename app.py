import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# ================= 檔案與路徑設定 =================
DATA_FILE = "data.csv"
SETTINGS_FILE = "settings.json"
IMG_DIR = "images"

# 確保圖片資料夾存在
os.makedirs(IMG_DIR, exist_ok=True)

# 系統頁面設定
st.set_page_config(page_title="工地品質管理系統", page_icon="🏗️", layout="wide")

# ================= 資料讀寫函數 =================
def load_settings():
    """讀取或初始化基礎設定(人員、工項)"""
    if not os.path.exists(SETTINGS_FILE):
        default_settings = {
            "personnel": ["工程師A", "主任B", "工地主任C"],
            "items": ["鋼筋綁紮", "模板組立", "混凝土澆置", "水電配管"]
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, ensure_ascii=False, indent=4)
        return default_settings
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(settings):
    """儲存基礎設定"""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

def load_data():
    """讀取或初始化回報資料(CSV)"""
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            "ID", "回報時間", "人員", "任務", "物件", "工項", "作業內容", "照片路徑", "狀態"
        ])
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
        return df
    try:
        # 使用 utf-8-sig 確保 Excel 開啟不會亂碼，dtype=str 防止 ID 變形
        return pd.read_csv(DATA_FILE, encoding="utf-8-sig", dtype=str)
    except Exception as e:
        st.error(f"讀取資料失敗: {e}")
        return pd.DataFrame()

def save_data(df):
    """儲存回報資料至 CSV"""
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

def save_uploaded_image(image_file, record_id):
    """儲存相機拍攝的照片，回傳存檔路徑"""
    if image_file is not None:
        file_path = os.path.join(IMG_DIR, f"{record_id}.jpg")
        with open(file_path, "wb") as f:
            f.write(image_file.getbuffer())
        return file_path
    return ""

# ================= 主程式與 UI =================
def main():
    # 載入資料
    settings = load_settings()
    df = load_data()

    # 側邊欄導覽
    st.sidebar.title("🏗️ 營建品質管理系統")
    page = st.sidebar.radio("切換功能", ["現場回報", "審核看板", "基礎資料管理"])

    if page == "現場回報":
        st.title("📍 現場作業回報")
        st.markdown("請填寫現場施作狀態，並附上照片後送出。")
        
        with st.form("report_form"):
            personnel_list = settings.get("personnel", [])
            item_list = settings.get("items", [])
            
            if not personnel_list or not item_list:
                st.warning("⚠️ 請先至「基礎資料管理」設定人員與工項清單！")
                st.form_submit_button("提交回報", disabled=True)
            else:
                # 適合手機的自適應排版
                col1, col2 = st.columns(2)
                with col1:
                    reporter = st.selectbox("1. 選擇人員", personnel_list)
                    task = st.text_input("2. 填寫任務", placeholder="例如：一樓結構")
                    obj = st.text_input("3. 填寫物件", placeholder="例如：C1 柱")
                with col2:
                    item = st.selectbox("4. 選擇工項", item_list)
                    content = st.text_area("5. 作業內容敘述", placeholder="請描述施作品質與狀況...")
                
                # 拍照功能 (st.camera_input 適合行動裝置與平板)
                st.markdown("**6. 現場拍照**")
                photo = st.camera_input("拍攝照片以供業主審查")
                
                # 提交按鈕
                submitted = st.form_submit_button("📩 提交回報", use_container_width=True)
                
                if submitted:
                    if not task.strip() or not obj.strip():
                        st.error("⚠️ 「任務」與「物件」不可為空白！")
                    elif photo is None:
                        st.error("⚠️ 請拍攝現場照片後再送出！")
                    else:
                        # 產生唯一 ID (以時間戳記)
                        new_id = datetime.now().strftime("%Y%m%d%H%M%S")
                        photo_path = save_uploaded_image(photo, new_id)
                        
                        new_row = {
                            "ID": new_id,
                            "回報時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "人員": reporter,
                            "任務": task.strip(),
                            "物件": obj.strip(),
                            "工項": item,
                            "作業內容": content.strip(),
                            "照片路徑": photo_path,
                            "狀態": "待審核"
                        }
                        
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(df)
                        st.success("✅ 回報已成功送出！")

    elif page == "審核看板":
        st.title("⚖️ 業主審核看板")
        st.markdown("檢視現場回報紀錄，並進行「合格」或「退回」審核。")
        
        if df.empty:
            st.info("目前沒有任何回報紀錄。")
        else:
            # 狀態看板與統計
            status_counts = df["狀態"].value_counts()
            pending_count = status_counts.get("待審核", 0)
            approved_count = status_counts.get("審核合格", 0)
            rejected_count = status_counts.get("退回修正", 0)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("⏳ 待審核", pending_count)
            c2.metric("✅ 審核合格", approved_count)
            c3.metric("❌ 退回修正", rejected_count)
            
            st.divider()
            
            # 篩選器，預設顯示待審核
            status_filter = st.selectbox("篩選狀態", ["全部", "待審核", "審核合格", "退回修正"], index=1)
            
            filtered_df = df
            if status_filter != "全部":
                filtered_df = df[df["狀態"] == status_filter]
            
            # 排序：最新的排前面
            filtered_df = filtered_df.sort_values(by="回報時間", ascending=False)
            
            for idx, row in filtered_df.iterrows():
                # 依狀態顯示不同圖示
                status_icon = "⏳" if row['狀態'] == '待審核' else ("✅" if row['狀態'] == '審核合格' else "❌")
                expander_title = f"{status_icon} [{row['狀態']}] {row['回報時間']} | {row['任務']} / {row['物件']} ({row['人員']})"
                
                # 待審核預設展開，其他收合
                with st.expander(expander_title, expanded=(row['狀態'] == '待審核')):
                    col_info, col_img = st.columns([1, 1])
                    with col_info:
                        st.markdown(f"**🔹 人員：** {row['人員']}")
                        st.markdown(f"**🔹 任務：** {row['任務']}")
                        st.markdown(f"**🔹 物件：** {row['物件']}")
                        st.markdown(f"**🔹 工項：** {row['工項']}")
                        st.markdown(f"**📝 作業內容：**")
                        st.info(row['作業內容'] if row['作業內容'] else "無特別說明")
                        st.markdown(f"**📌 目前狀態：** `{row['狀態']}`")
                        
                        # 操作按鈕 (僅待審核狀態顯示)
                        if row['狀態'] == "待審核":
                            st.markdown("### 審核操作")
                            btn_c1, btn_c2 = st.columns(2)
                            with btn_c1:
                                if st.button("✅ 審核合格", key=f"approve_{row['ID']}", use_container_width=True):
                                    df.loc[df["ID"] == row["ID"], "狀態"] = "審核合格"
                                    save_data(df)
                                    st.rerun()
                            with btn_c2:
                                if st.button("❌ 退回修正", key=f"reject_{row['ID']}", use_container_width=True):
                                    df.loc[df["ID"] == row["ID"], "狀態"] = "退回修正"
                                    save_data(df)
                                    st.rerun()
                                    
                    with col_img:
                        if pd.notna(row['照片路徑']) and os.path.exists(row['照片路徑']):
                            st.image(row['照片路徑'], caption="現場拍攝照片", use_container_width=True)
                        else:
                            st.warning("照片遺失或無照片")

    elif page == "基礎資料管理":
        st.title("⚙️ 基礎資料管理 (後台)")
        st.markdown("在此維護系統共用的預設清單，變更將直接反映在現場回報的選單中。")
        
        col_p, col_i = st.columns(2)
        with col_p:
            st.subheader("👤 人員清單")
            personnel_text = st.text_area(
                "編輯人員 (請每行輸入一位)：", 
                value="\n".join(settings.get("personnel", [])), 
                height=250
            )
        
        with col_i:
            st.subheader("🛠️ 工項清單")
            items_text = st.text_area(
                "編輯工項 (請每行輸入一項)：", 
                value="\n".join(settings.get("items", [])), 
                height=250
            )
        
        st.warning("⚠️ 編輯完成後，請點擊下方按鈕以套用變更")
        if st.button("💾 儲存所有設定", use_container_width=True):
            new_personnel = [p.strip() for p in personnel_text.split("\n") if p.strip()]
            new_items = [i.strip() for i in items_text.split("\n") if i.strip()]
            
            # 防呆機制：避免全部清空而導致報錯
            if not new_personnel:
                new_personnel = ["請新增人員"]
            if not new_items:
                new_items = ["請新增工項"]
                
            settings["personnel"] = new_personnel
            settings["items"] = new_items
            save_settings(settings)
            st.success("✅ 基礎資料已成功更新！")

if __name__ == "__main__":
    main()
