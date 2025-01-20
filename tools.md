<!--
 * @Author: zjzjzjzj1874 zjzjzjzj1874@gmail.com
 * @Date: 2025-01-20 10:10:05
 * @LastEditors: zjzjzjzj1874 zjzjzjzj1874@gmail.com
 * @LastEditTime: 2025-01-20 10:10:34
 * @FilePath: /bill-py-streamlit/tools.md
 * @Description: 常用sql查询
-->
# Tools

## 常用查询
```sql
// 查询某一项明细
db.bills.find({"remark": {$regex: "满彭", $options: "i"}})
// 查询某一项所有花费
db.bills.aggregate([{$match: {"remark": { $regex: "满彭", $options: "i" }}},{$group: {_id: null,totalAmount: { $sum: "$amount" }}}])
```