# 動態外務跑店自動分群與路線規劃器

這是一個 Streamlit 小工具，可直接貼上每日巡店清單，自動比對雙北家樂福超市資料、依地理分區拆路線、排機車拜訪順序，並產生可轉傳 LINE 的時程文字與 Google Maps 導航連結。

## 安裝

```powershell
pip install -r requirements.txt
```

## 執行

```powershell
streamlit run app.py
```

## 使用方式

1. 在左側設定出發時間、每店停留分鐘數、機車平均時速。
2. 將業務給的店名清單貼到文字框，一行一店；也可以直接貼 LINE 訊息，程式會自動清掉序號、時間與導航文字。
3. 按下「開始規劃今日路線」。
4. 先看跨區摘要：如果涵蓋 4 個以上區域，畫面會跳出紅色防呆警告。
5. 選擇只跑單一路線，或硬著頭皮全跑。
6. 複製下方 LINE 文字，或開啟 Google Maps 導航連結。

## Google Distance Matrix API

目前預設使用離線估算：經緯度直線距離乘以道路修正係數，再用機車時速換算時間。

若要改用 Google Distance Matrix API，可在介面貼上 API Key，程式會優先呼叫 Google API；若失敗會自動回到離線估算。

## 門市資料

程式內建家樂福官方超市清單中的台北市與新北市超市門市，已排除基隆、汐止、淡水與大型量販店。門市開閉店會變動，建議定期依家樂福官方分店資訊更新 `OFFICIAL_MARKET_ROWS`。

目前導航連結會使用完整地址開啟 Google Maps；經緯度主要用於程式內部分群與排序。

## 手機使用與雲端部署

介面已針對手機寬度調整：多欄會自動改為單欄，按鈕會使用全寬顯示。

部署到 Streamlit Community Cloud 後，手機可直接透過 `https://...streamlit.app` 網址使用，不需要連到本機 `localhost:8501`。

詳細步驟請參考 [DEPLOY_STREAMLIT_CLOUD.md](DEPLOY_STREAMLIT_CLOUD.md)。
