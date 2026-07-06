from __future__ import annotations
import threading
import queue

class FloatingOrb:
    """Small always-on-top status orb. Works without crashing if Tkinter is unavailable."""
    def __init__(self):
        self.q = queue.Queue()
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def update(self, status: str, line: str = ''):
        self.q.put((status, line))

    def _run(self):
        try:
            import tkinter as tk
            root = tk.Tk()
            root.title('Blue Orb')
            root.attributes('-topmost', True)
            root.geometry('300x130+40+40')
            root.configure(bg='#07111f')
            status_lbl = tk.Label(root, text='BLUE', fg='#7dd3fc', bg='#07111f', font=('Segoe UI', 20, 'bold'))
            status_lbl.pack(pady=(18, 4))
            line_lbl = tk.Label(root, text='Ready', fg='white', bg='#07111f', wraplength=260, font=('Segoe UI', 10))
            line_lbl.pack()
            def poll():
                while not self.q.empty():
                    status, line = self.q.get_nowait()
                    status_lbl.config(text=status.upper())
                    line_lbl.config(text=line[:120])
                root.after(200, poll)
            poll()
            root.mainloop()
        except Exception:
            pass

orb = FloatingOrb()
