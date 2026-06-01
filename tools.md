<!--
 * @Description: 常用sql查询
-->
# Tools

## 常用查询
```sql
// 查询某一项明细
db.bills.find({"remark": {$regex: "关键词", $options: "i"}})
// 查询某一项所有花费
db.bills.aggregate([{$match: {"remark": { $regex: "关键词", $options: "i" }}},{$group: {_id: null,totalAmount: { $sum: "$amount" }}}])
```