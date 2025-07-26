duplicate_checker/         <-- 项目根目录
│
├── core/                  <-- 核心功能模块
│   ├── __init__.py
│   ├── file_utils.py      <-- 文件收集、重复检测等逻辑
│   └── utils.py           <-- 一些通用辅助函数，比如字符串处理、正则等
│
├── gui/                   <-- 图形界面相关代码
│   ├── __init__.py
│   └── main_window.py     <-- GUI主窗口及界面逻辑
│
├── tests/                 <-- 测试代码（以后可以补充）
│   ├── __init__.py
│   └── test_file_utils.py
│
├── requirements.txt       <-- 依赖列表（如send2trash等）
├── README.md              <-- 项目说明文档
└── run.py                 <-- 程序入口，启动GUI
