# 1. 初始化迁移
flask db init

# 2. 创建迁移脚本
flask db migrate -m "rename command history columns"

# 3. 应用迁移
flask db upgrade 