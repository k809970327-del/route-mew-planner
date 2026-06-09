# 部署到 Streamlit Community Cloud

## 專案必要檔案

```text
app.py
requirements.txt
.streamlit/config.toml
assets/korean_route_hero.png
```

本機桌面啟動檔可以保留，但部署不會使用：

```text
start_route_planner.ps1
start_route_planner_public.ps1
```

## 部署步驟

1. 在 GitHub 建立新的 repository。
2. 將本專案上傳到 repository。
3. 前往 https://share.streamlit.io/ 並連結 GitHub。
4. 點選 `Create app`。
5. 選擇 repository、branch，Entrypoint file 填入：

```text
app.py
```

6. Python 版本建議選擇 `3.12`。
7. 點選 Deploy。

部署完成後會取得可在手機開啟的網址：

```text
https://你的網址.streamlit.app
```

## Google Distance Matrix API Key

API Key 不要上傳到 GitHub。

如需設定，在 Streamlit Community Cloud 的 App settings > Secrets 加入：

```toml
GOOGLE_DISTANCE_MATRIX_API_KEY = "你的 API Key"
```

沒有設定 API Key 時，App 仍可使用經緯度離線估算距離。

## 未完成記憶

- 本機版會保存至 `pending_store_list.json`。
- 雲端版會在目前瀏覽器連線期間使用 Session State。
- Streamlit Community Cloud 重啟、休眠或重新部署後，不保證保留本機 JSON 資料。

## 手機與上傳功能

- 手機版已將多欄排版自動改為單欄，按鈕改為全寬。
- 目前 App 沒有檔案上傳或照片上傳功能，因此不需要手機相機權限。
- 如未來新增照片功能，建議使用 `st.camera_input` 或 `st.file_uploader`。

## 部署前檢查

```powershell
python -m py_compile app.py
streamlit run app.py
```
