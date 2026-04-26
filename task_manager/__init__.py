"""使 Django 的 mysql 后端使用 PyMySQL（纯 Python，Windows 上安装简单）。"""
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    pass
