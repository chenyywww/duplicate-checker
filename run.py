import tkinter as tk
from gui.main_window import DuplicateCheckerGUI

def main():
    root = tk.Tk()
    app = DuplicateCheckerGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
