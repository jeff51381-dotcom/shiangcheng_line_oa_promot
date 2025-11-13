# 產品分類與 CPC 映射說明

這份文件說明如何在專案中使用統一的產品分類對應到台灣中油（CPC）的產品分類頁面。

已納入的分類：
- 車輛用油
  - CPC 連結: https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=13
  - CSN: 13
- 海運用油
  - CPC 連結: https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=14
  - CSN: 14
- 工業用油
  - CPC 連結: https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=64
  - CSN: 64
- 滑脂
  - CPC 連結: https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=76
  - CSN: 76
- 基礎油
  - CPC 連結: https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=77
  - CSN: 77

整合建議：
1. 將 `product_classification.py` 放在專案的頂層或 utils/module 資料夾中，並在需要用到產品分類的地方引用 `classify()` 與 `CPC_CATEGORIES`。
2. 在建立或更新商品資料時，使用 `classify(product.category)` 給商品帶入 canonical classification 與 cpc_url、cpc_csn 等欄位。
3. 若資料庫 schema 允許，可新增欄位：
   - cpc_category_name (string)
   - cpc_csn (string)
   - cpc_url (string)
   由後端在儲存時填入，或在前端顯示時透過查表查詢（避免資料重複）。
4. 若需要支援更多同義詞或語言，請在 `SYNONYMS` 中補上對應關係。

範例 (Django ORM)：
```python
# models.py
class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)  # 原始分類
    cpc_category_name = models.CharField(max_length=255, null=True, blank=True)
    cpc_csn = models.CharField(max_length=32, null=True, blank=True)
    cpc_url = models.URLField(null=True, blank=True)

# signals or save hook
from product_classification import classify
info = classify(instance.category)
if info:
    instance.cpc_category_name = info['cpc_name']
    instance.cpc_csn = info['cpc_csn']
    instance.cpc_url = info['cpc_url']
```

後續建議：
- 若你希望我直接把 `product_classification.py` 新增到專案並提交成一個 commit，我可以幫你產生要 push 的內容（或直接呼叫 GitHub 操作來建立檔案），請告訴我你要我幫你做哪一項。