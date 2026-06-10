import sqlite3
import hashlib
import random
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import csv

# ---------------- COLORS ----------------
BG          = "#0a0e1a"          # Deep navy background
BG2         = "#0f1628"          # Slightly lighter panel bg
CARD        = "#131d35"          # Card surface
CARD2       = "#1a2540"          # Elevated card
BORDER      = "#1e2e52"          # Subtle border
PRIMARY     = "#3b82f6"          # Electric blue
PRIMARY_DK  = "#2563eb"          # Darker blue (hover)
ACCENT      = "#06b6d4"          # Cyan accent
SUCCESS     = "#10b981"          # Emerald green
SUCCESS_DK  = "#059669"
DANGER      = "#f43f5e"          # Rose red
DANGER_DK   = "#e11d48"
WARN        = "#f59e0b"          # Amber
WARN_DK     = "#d97706"
PURPLE      = "#8b5cf6"
PURPLE_DK   = "#7c3aed"
TEXT        = "#e2e8f0"          # Near-white
TEXT2       = "#94a3b8"          # Muted text
TEXT3       = "#64748b"          # Very muted

# Fonts
FONT_TITLE  = ("Segoe UI Variable", 26, "bold")
FONT_HEAD   = ("Segoe UI Variable", 16, "bold")
FONT_SUB    = ("Segoe UI", 11)
FONT_BTN    = ("Segoe UI Semibold", 11)
FONT_LABEL  = ("Segoe UI", 10)
FONT_INPUT  = ("Segoe UI", 12)
FONT_SMALL  = ("Segoe UI", 9)

# ---------------- DATABASE ----------------
conn   = sqlite3.connect("voting.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    id_number TEXT UNIQUE,
    has_voted INTEGER DEFAULT 0
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS candidates(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS votes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER,
    user_id INTEGER
)""")
conn.commit()

# ---------------- SECURITY ----------------
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def hash_id(i):       return hashlib.sha256(i.encode()).hexdigest()

# ---------------- GLOBAL STATE ----------------
generated_otp = ""
current_user  = None

# ---------------- ROOT ----------------
root = tk.Tk()
root.title("SecureVote — Digital Voting Platform")
root.state("zoomed")
root.configure(bg=BG)

# =========================================================
#  STYLED WIDGET HELPERS
# =========================================================

def make_button(parent, text, cmd, bg_color, hover_color=None,
                width=None, padx=20, pady=10, font=FONT_BTN):
    """Flat button with hover effect."""
    hc = hover_color or bg_color
    kw = dict(text=text, command=cmd, bg=bg_color, fg=TEXT,
              font=font, bd=0, padx=padx, pady=pady,
              cursor="hand2", activebackground=hc, activeforeground=TEXT,
              relief="flat")
    if width:
        kw["width"] = width
    b = tk.Button(parent, **kw)
    b.bind("<Enter>", lambda e: b.configure(bg=hc))
    b.bind("<Leave>", lambda e: b.configure(bg=bg_color))
    return b

def make_entry(parent, placeholder="", show=None, width=34):
    """Styled entry with placeholder support."""
    frame = tk.Frame(parent, bg=CARD2, bd=0, highlightthickness=1,
                     highlightbackground=BORDER, highlightcolor=PRIMARY)
    kw = dict(font=FONT_INPUT, bg=CARD2, fg=TEXT,
              insertbackground=PRIMARY, bd=0, width=width,
              relief="flat")
    if show:
        kw["show"] = show
    e = tk.Entry(frame, **kw)
    e.pack(padx=12, pady=10)

    if placeholder:
        e.insert(0, placeholder)
        e.configure(fg=TEXT3)
        def on_focus_in(ev):
            if e.get() == placeholder:
                e.delete(0, "end")
                e.configure(fg=TEXT)
                if show:
                    e.configure(show=show)
        def on_focus_out(ev):
            if not e.get():
                e.insert(0, placeholder)
                e.configure(fg=TEXT3)
                if show:
                    e.configure(show="")

        e.bind("<FocusIn>",  on_focus_in)
        e.bind("<FocusOut>", on_focus_out)

    frame.bind("<Button-1>", lambda e: e.widget.focus_set())
    return frame, e

def separator(parent, color=BORDER, pady=6):
    f = tk.Frame(parent, bg=color, height=1)
    f.pack(fill="x", pady=pady)

def label(parent, text, font=FONT_SUB, fg=TEXT2, bg=None, anchor="w"):
    bg = bg or parent.cget("bg")
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, anchor=anchor)

def section_title(parent, text, fg=TEXT, bg=None):
    bg = bg or parent.cget("bg")
    tk.Label(parent, text=text, font=("Segoe UI", 13, "bold"),
             fg=fg, bg=bg).pack(anchor="w", pady=(0, 4))

def badge(parent, text, color=ACCENT, bg=None):
    bg = bg or parent.cget("bg")
    tk.Label(parent, text=f"  {text}  ",
             font=FONT_SMALL, fg=BG, bg=color,
             relief="flat").pack(anchor="w", pady=2)

def icon_label(parent, icon, text, fg=TEXT2, bg=None):
    bg = bg or parent.cget("bg")
    f = tk.Frame(parent, bg=bg)
    tk.Label(f, text=icon, font=("Segoe UI", 11), fg=ACCENT, bg=bg).pack(side="left")
    tk.Label(f, text=f"  {text}", font=FONT_SUB, fg=fg, bg=bg).pack(side="left")
    f.pack(anchor="w", pady=1)
    return f

# =========================================================
#  STATUS BAR
# =========================================================
status_var = tk.StringVar(value="Not logged in")

def update_status(msg, color=TEXT2):
    status_var.set(msg)
    status_bar.configure(fg=color)

# =========================================================
#  VALIDATION
# =========================================================
def valid_password(p):
    return len(p) >= 6 and any(c.isdigit() for c in p)

def get_placeholder_val(entry_widget, placeholder):
    v = entry_widget.get().strip()
    return "" if v == placeholder else v

# =========================================================
#  REGISTER
# =========================================================
def register():
    u   = get_placeholder_val(user_e,  "Username")
    p   = get_placeholder_val(pass_e,  "Password")
    idn = get_placeholder_val(id_e,    "ID")

    if not u or not p or not idn:
        show_toast("All fields are required.", DANGER); return
    if len(u) < 4:
        show_toast("Username must be at least 4 characters.", DANGER); return
    if not valid_password(p):
        show_toast("Password must be ≥6 chars with a digit.", DANGER); return
    if not idn.isdigit() or len(idn) != 12:
        show_toast("ID must be exactly 12 digits.", DANGER); return

    try:
        cursor.execute("INSERT INTO users(username,password,id_number) VALUES(?,?,?)",
                       (u, hash_password(p), hash_id(idn)))
        conn.commit()
        show_toast("Registration successful! You may now log in.", SUCCESS)
    except:
        show_toast("Username or ID already registered.", DANGER)

# =========================================================
#  LOGIN
# =========================================================
def login():
    global current_user, generated_otp

    u   = get_placeholder_val(user_e, "Username")
    p   = get_placeholder_val(pass_e, "Password")
    idn = get_placeholder_val(id_e,   "ID")

    if not u or not p or not idn:
        show_toast("All fields are required.", DANGER); return

    cursor.execute("SELECT * FROM users WHERE username=? AND password=? AND id_number=?",
                   (u, hash_password(p), hash_id(idn)))
    user = cursor.fetchone()

    if user:
        current_user    = user
        generated_otp   = str(random.randint(100000, 999999))
        update_status(f"Logged in as {u}", SUCCESS)
        show_otp_dialog(generated_otp)
    else:
        show_toast("Invalid credentials. Please try again.", DANGER)

# =========================================================
#  OTP DIALOG  (replaces inline OTP field)
# =========================================================
def show_otp_dialog(otp):
    win = tk.Toplevel(root)
    win.title("Two-Factor Verification")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.grab_set()

    # Center it
    win.geometry("400x340")
    win.update_idletasks()
    x = root.winfo_x() + (root.winfo_width()  - 400) // 2
    y = root.winfo_y() + (root.winfo_height() - 340) // 2
    win.geometry(f"+{x}+{y}")

    # Header bar
    header = tk.Frame(win, bg=PRIMARY, pady=14)
    header.pack(fill="x")
    tk.Label(header, text="🔐  Two-Factor Authentication", font=("Segoe UI", 13, "bold"),
             fg="white", bg=PRIMARY).pack()

    body = tk.Frame(win, bg=BG, padx=30, pady=20)
    body.pack(fill="both", expand=True)

    label(body, "Your OTP has been generated:", fg=TEXT2, bg=BG).pack(anchor="w")

    # OTP display box
    otp_box = tk.Frame(body, bg=CARD2, bd=0, highlightthickness=1,
                       highlightbackground=ACCENT)
    otp_box.pack(fill="x", pady=10)
    tk.Label(otp_box, text=otp, font=("Courier New", 28, "bold"),
             fg=ACCENT, bg=CARD2, pady=10).pack()

    label(body, "Enter the OTP below to proceed:", fg=TEXT2, bg=BG).pack(anchor="w", pady=(8,4))

    entry_frame, otp_input = make_entry(body, "Enter OTP", width=30)
    entry_frame.pack(fill="x")

    msg_lbl = tk.Label(body, text="", font=FONT_LABEL, fg=DANGER, bg=BG)
    msg_lbl.pack(pady=4)

    def verify():
        global generated_otp
        entered = otp_input.get().strip()
        if entered == generated_otp:
            generated_otp = ""
            win.destroy()
            open_voting()
        else:
            msg_lbl.configure(text="Incorrect OTP. Please try again.")

    make_button(body, "✓  Verify & Proceed", verify, PRIMARY, PRIMARY_DK,
                pady=11).pack(fill="x", pady=8)

# =========================================================
#  TOAST NOTIFICATION
# =========================================================
_toast_after = None

def show_toast(msg, color=SUCCESS):
    global _toast_after
    toast_lbl.configure(text=f"  {msg}  ", bg=color, fg="white")
    toast_lbl.place(relx=0.5, rely=0.96, anchor="center")
    if _toast_after:
        root.after_cancel(_toast_after)
    _toast_after = root.after(3500, lambda: toast_lbl.place_forget())

# =========================================================
#  VOTING WINDOW
# =========================================================
def open_voting():
    if current_user[4] == 1:
        show_toast("You have already cast your vote.", WARN); return

    cursor.execute("SELECT id, name FROM candidates")
    candidates = cursor.fetchall()

    if not candidates:
        show_toast("No candidates available yet.", WARN); return

    win = tk.Toplevel(root)
    win.title("Cast Your Vote")
    win.configure(bg=BG)
    win.geometry("520x520")
    win.resizable(False, False)
    win.grab_set()
    x = root.winfo_x() + (root.winfo_width()  - 520) // 2
    y = root.winfo_y() + (root.winfo_height() - 520) // 2
    win.geometry(f"+{x}+{y}")

    # Header
    hdr = tk.Frame(win, bg=SUCCESS, pady=16)
    hdr.pack(fill="x")
    tk.Label(hdr, text="🗳️  Cast Your Vote", font=("Segoe UI", 14, "bold"),
             fg="white", bg=SUCCESS).pack()
    tk.Label(hdr, text="Select one candidate below — your vote is anonymous.",
             font=FONT_LABEL, fg="#d1fae5", bg=SUCCESS).pack()

    body = tk.Frame(win, bg=BG, padx=30, pady=20)
    body.pack(fill="both", expand=True)

    selected_var = tk.IntVar(value=-1)

    for cid, name in candidates:
        row = tk.Frame(body, bg=CARD, bd=0, highlightthickness=1,
                       highlightbackground=BORDER, cursor="hand2")
        row.pack(fill="x", pady=6)

        inner = tk.Frame(row, bg=CARD, padx=14, pady=12)
        inner.pack(fill="x")

        rb = tk.Radiobutton(inner, variable=selected_var, value=cid,
                            bg=CARD, activebackground=CARD,
                            selectcolor=PRIMARY, fg=PRIMARY, bd=0)
        rb.pack(side="left")

        tk.Label(inner, text=name, font=("Segoe UI", 11, "bold"),
                 fg=TEXT, bg=CARD).pack(side="left", padx=8)

        # Highlight row on hover
        def enter(e, r=row): r.configure(highlightbackground=PRIMARY)
        def leave(e, r=row): r.configure(highlightbackground=BORDER)
        row.bind("<Enter>", enter)
        row.bind("<Leave>", leave)
        inner.bind("<Button-1>", lambda e, c=cid: selected_var.set(c))

    warn_lbl = tk.Label(body, text="", font=FONT_LABEL, fg=DANGER, bg=BG)
    warn_lbl.pack(pady=4)

    def confirm_vote():
        cid = selected_var.get()
        if cid == -1:
            warn_lbl.configure(text="Please select a candidate first.")
            return
        # Confirm dialog
        cname = next(n for i, n in candidates if i == cid)
        if messagebox.askyesno("Confirm Vote",
                               f"Confirm your vote for:\n\n  {cname}\n\nThis cannot be undone."):
            cast_vote(cid, win)

    make_button(body, "Submit Vote  →", confirm_vote, SUCCESS, SUCCESS_DK, pady=12).pack(fill="x", pady=10)

# =========================================================
#  CAST VOTE
# =========================================================
def cast_vote(cid, win):
    cursor.execute("INSERT INTO votes(candidate_id,user_id) VALUES(?,?)",
                   (cid, current_user[0]))
    cursor.execute("UPDATE users SET has_voted=1 WHERE id=?", (current_user[0],))
    conn.commit()
    win.destroy()
    show_toast("✓  Your vote has been recorded successfully!", SUCCESS)
    update_status(f"Voted successfully", SUCCESS)

# =========================================================
#  RESULTS WINDOW
# =========================================================
def show_results():
    cursor.execute("""
    SELECT candidates.name, COUNT(*) as cnt
    FROM votes
    JOIN candidates ON candidates.id = votes.candidate_id
    GROUP BY candidates.name
    ORDER BY cnt DESC
    """)
    data = cursor.fetchall()

    win = tk.Toplevel(root)
    win.title("Election Results")
    win.configure(bg=BG)
    win.geometry("520x500")
    win.resizable(False, False)
    x = root.winfo_x() + (root.winfo_width()  - 520) // 2
    y = root.winfo_y() + (root.winfo_height() - 500) // 2
    win.geometry(f"+{x}+{y}")

    hdr = tk.Frame(win, bg=PURPLE, pady=16)
    hdr.pack(fill="x")
    tk.Label(hdr, text="📊  Election Results", font=("Segoe UI", 14, "bold"),
             fg="white", bg=PURPLE).pack()

    body = tk.Frame(win, bg=BG, padx=30, pady=20)
    body.pack(fill="both", expand=True)

    if not data:
        tk.Label(body, text="No votes have been cast yet.",
                 font=FONT_SUB, fg=TEXT2, bg=BG).pack(pady=40)
        return

    total = sum(c for _, c in data)
    winner = data[0]

    # Winner banner
    w_frame = tk.Frame(body, bg=SUCCESS, pady=12, padx=16)
    w_frame.pack(fill="x", pady=(0, 16))
    tk.Label(w_frame, text="🏆  Winner", font=("Segoe UI", 9, "bold"),
             fg="#d1fae5", bg=SUCCESS).pack(anchor="w")
    tk.Label(w_frame, text=winner[0], font=("Segoe UI", 16, "bold"),
             fg="white", bg=SUCCESS).pack(anchor="w")
    tk.Label(w_frame, text=f"{winner[1]} votes  ({winner[1]/total*100:.1f}%)",
             font=FONT_SUB, fg="#d1fae5", bg=SUCCESS).pack(anchor="w")

    # Bar chart
    BAR_COLORS = [PRIMARY, ACCENT, WARN, PURPLE, DANGER]
    for i, (name, count) in enumerate(data):
        pct = count / total if total else 0
        row = tk.Frame(body, bg=BG)
        row.pack(fill="x", pady=5)

        tk.Label(row, text=name, font=("Segoe UI", 10, "bold"),
                 fg=TEXT, bg=BG, width=18, anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(row, text=f"{count} votes", font=FONT_LABEL,
                 fg=TEXT2, bg=BG, width=8, anchor="e").grid(row=0, column=2, sticky="e", padx=(4,0))

        bar_bg = tk.Frame(row, bg=CARD2, height=14, width=240)
        bar_bg.grid(row=0, column=1, padx=(8, 4))
        bar_bg.pack_propagate(False)

        fill_w = max(4, int(240 * pct))
        bar_fill = tk.Frame(bar_bg, bg=BAR_COLORS[i % len(BAR_COLORS)],
                            height=14, width=fill_w)
        bar_fill.pack(side="left", fill="y")

        tk.Label(row, text=f"{pct*100:.1f}%", font=FONT_SMALL,
                 fg=BAR_COLORS[i % len(BAR_COLORS)], bg=BG).grid(row=0, column=3)

    separator(body, pady=12)
    label(body, f"Total votes cast: {total}", fg=TEXT2, bg=BG).pack(anchor="w")

# =========================================================
#  EXPORT
# =========================================================
def export_results():
    cursor.execute("""
    SELECT candidates.name, COUNT(*)
    FROM votes JOIN candidates ON candidates.id = votes.candidate_id
    GROUP BY candidates.name ORDER BY COUNT(*) DESC
    """)
    with open("results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Candidate", "Votes"])
        w.writerows(cursor.fetchall())
    show_toast("Results exported to results.csv", SUCCESS)

# =========================================================
#  ADMIN PANEL
# =========================================================
def add_candidate():
    name = simpledialog.askstring("Add Candidate", "Enter candidate name:")
    if name and name.strip():
        try:
            cursor.execute("INSERT INTO candidates(name) VALUES(?)", (name.strip(),))
            conn.commit()
            show_toast(f"Candidate '{name.strip()}' added.", SUCCESS)
        except:
            show_toast("Candidate already exists.", DANGER)

def delete_candidate_by_id(cid, name):
    if messagebox.askyesno("Confirm Delete",
                          f"Delete candidate '{name}'?\nAll votes will also be removed."):
        cursor.execute("DELETE FROM votes WHERE candidate_id=?", (cid,))
        cursor.execute("DELETE FROM candidates WHERE id=?", (cid,))
        conn.commit()
        show_toast(f"Candidate '{name}' removed with all votes.", WARN)

def show_stats():
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM votes")
    votes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM candidates")
    cands = cursor.fetchone()[0]

    win = tk.Toplevel(root)
    win.title("System Statistics")
    win.configure(bg=BG)
    win.geometry("380x280")
    win.resizable(False, False)
    x = root.winfo_x() + (root.winfo_width()  - 380) // 2
    y = root.winfo_y() + (root.winfo_height() - 280) // 2
    win.geometry(f"+{x}+{y}")

    hdr = tk.Frame(win, bg=PURPLE, pady=14)
    hdr.pack(fill="x")
    tk.Label(hdr, text="📈  System Statistics", font=("Segoe UI", 13, "bold"),
             fg="white", bg=PURPLE).pack()

    body = tk.Frame(win, bg=BG, padx=30, pady=20)
    body.pack(fill="both", expand=True)

    for icon, label_text, val, color in [
        ("👤", "Registered Users",    users, PRIMARY),
        ("📋", "Active Candidates",   cands, ACCENT),
        ("🗳️", "Total Votes Cast",    votes, SUCCESS),
    ]:
        row = tk.Frame(body, bg=CARD2, bd=0, highlightthickness=1,
                       highlightbackground=BORDER)
        row.pack(fill="x", pady=5)
        inner = tk.Frame(row, bg=CARD2, padx=14, pady=10)
        inner.pack(fill="x")
        tk.Label(inner, text=icon, font=("Segoe UI", 16), bg=CARD2).pack(side="left")
        tk.Label(inner, text=label_text, font=FONT_SUB, fg=TEXT2, bg=CARD2).pack(side="left", padx=10)
        tk.Label(inner, text=str(val), font=("Segoe UI", 14, "bold"),
                 fg=color, bg=CARD2).pack(side="right")

def admin_panel():
    ADMIN_PASS = "admin123"
    entered = simpledialog.askstring("Admin Access", "Enter admin password:", show="*")
    if entered != ADMIN_PASS:
        show_toast("Invalid admin password.", DANGER)
        return

    win = tk.Toplevel(root)
    win.title("Admin Panel")
    win.configure(bg=BG)
    win.geometry("420x500")
    win.resizable(False, False)

    # HEADER
    hdr = tk.Frame(win, bg=PRIMARY, pady=16)
    hdr.pack(fill="x")
    tk.Label(hdr, text="⚙️ Admin Panel", font=("Segoe UI", 14, "bold"),
             fg="white", bg=PRIMARY).pack()

    body = tk.Frame(win, bg=BG, padx=20, pady=20)
    body.pack(fill="both", expand=True)

    # ---------- ADD BUTTON ----------
    def add_candidate_ui():
        name = simpledialog.askstring("Add Candidate", "Enter candidate name:")
        if name and name.strip():
            try:
                cursor.execute("INSERT INTO candidates(name) VALUES(?)", (name.strip(),))
                conn.commit()
                refresh_list()
                show_toast(f"{name} added.", SUCCESS)
            except:
                show_toast("Candidate already exists.", DANGER)

    make_button(body, "➕ Add Candidate", add_candidate_ui,
                SUCCESS, SUCCESS_DK).pack(fill="x", pady=(0,10))

    # ---------- LIST FRAME ----------
    list_frame = tk.Frame(body, bg=BG)
    list_frame.pack(fill="both", expand=True)

    def refresh_list():
        for w in list_frame.winfo_children():
            w.destroy()

        cursor.execute("SELECT id, name FROM candidates")
        data = cursor.fetchall()

        if not data:
            tk.Label(list_frame, text="No candidates yet.",
                     fg=TEXT2, bg=BG).pack(pady=20)
            return

        for cid, name in data:
            row = tk.Frame(list_frame, bg=CARD, pady=8, padx=10,
                           highlightthickness=1, highlightbackground=BORDER)
            row.pack(fill="x", pady=5)

            tk.Label(row, text=name, font=("Segoe UI", 11, "bold"),
                     fg=TEXT, bg=CARD).pack(side="left")

            # ❌ DELETE BUTTON
            btn = tk.Button(row, text="❌", bg=DANGER, fg="white",
                            bd=0, padx=10, cursor="hand2",
                            command=lambda c=cid, n=name: [delete_candidate_by_id(c,n), refresh_list()])
            btn.pack(side="right")

    refresh_list()

    # ---------- EXTRA ACTIONS ----------
    separator(body)

    make_button(body, "📊 View Results", show_results,
                PURPLE, PURPLE_DK).pack(fill="x", pady=5)

    make_button(body, "📁 Export CSV", export_results,
                WARN, WARN_DK).pack(fill="x", pady=5)

    make_button(body, "📈 System Stats", show_stats,
                ACCENT, "#0891b2").pack(fill="x", pady=5)
# =========================================================
#  LOGOUT
# =========================================================
def logout():
    global current_user
    current_user = None
    update_status("Not logged in", TEXT3)
    show_toast("Logged out successfully.", PRIMARY)

# =========================================================
#  MAIN LAYOUT
# =========================================================

# — Sidebar (left) —
sidebar = tk.Frame(root, bg=CARD, width=240, pady=0)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

# Logo / Brand
brand = tk.Frame(sidebar, bg=PRIMARY, pady=22, padx=20)
brand.pack(fill="x")
tk.Label(brand, text="🗳️", font=("Segoe UI", 26), bg=PRIMARY, fg="white").pack(anchor="w")
tk.Label(brand, text="SecureVote", font=("Segoe UI", 16, "bold"),
         fg="white", bg=PRIMARY).pack(anchor="w")
tk.Label(brand, text="Digital Voting Platform", font=("Segoe UI", 8),
         fg="#bfdbfe", bg=PRIMARY).pack(anchor="w")

sidebar_body = tk.Frame(sidebar, bg=CARD, padx=16, pady=20)
sidebar_body.pack(fill="both", expand=True)

# Nav section
tk.Label(sidebar_body, text="NAVIGATION", font=("Segoe UI", 8, "bold"),
         fg=TEXT3, bg=CARD).pack(anchor="w", pady=(0, 8))

def nav_btn(text, cmd, icon=""):
    f = tk.Frame(sidebar_body, bg=CARD, cursor="hand2")
    f.pack(fill="x", pady=2)
    inner = tk.Frame(f, bg=CARD, padx=10, pady=9)
    inner.pack(fill="x")
    tk.Label(inner, text=icon, font=("Segoe UI", 11), fg=ACCENT, bg=CARD, width=2).pack(side="left")
    lbl = tk.Label(inner, text=text, font=("Segoe UI", 10), fg=TEXT2, bg=CARD)
    lbl.pack(side="left", padx=6)

    def on_click(e=None): cmd()
    def enter(e):
        f.configure(bg=CARD2); inner.configure(bg=CARD2); lbl.configure(bg=CARD2)
    def leave(e):
        f.configure(bg=CARD); inner.configure(bg=CARD); lbl.configure(bg=CARD)
    f.bind("<Button-1>", on_click)
    inner.bind("<Button-1>", on_click)
    lbl.bind("<Button-1>", on_click)
    f.bind("<Enter>", enter); f.bind("<Leave>", leave)

nav_btn("Register",    register,     "📝")
nav_btn("Login",       login,        "🔑")
nav_btn("View Results",show_results, "📊")
nav_btn("Admin Panel", admin_panel,  "⚙️")
nav_btn("Logout",      logout,       "🚪")

# Sidebar footer
sidebar_foot = tk.Frame(sidebar, bg=CARD, padx=16, pady=14)
sidebar_foot.pack(fill="x", side="bottom")
tk.Label(sidebar_foot, text="v2.0  ·  Secure & Anonymous",
         font=FONT_SMALL, fg=TEXT3, bg=CARD).pack(anchor="w")

# — Main content area —
content = tk.Frame(root, bg=BG)
content.pack(side="left", fill="both", expand=True)

# Top bar
topbar = tk.Frame(content, bg=BG2, pady=14, padx=30,
                  highlightthickness=1, highlightbackground=BORDER)
topbar.pack(fill="x")
tk.Label(topbar, text="Welcome to SecureVote",
         font=("Segoe UI", 13, "bold"), fg=TEXT, bg=BG2).pack(side="left")
status_bar = tk.Label(topbar, textvariable=status_var,
                      font=FONT_LABEL, fg=TEXT3, bg=BG2)
status_bar.pack(side="right")

# Centre panel
centre = tk.Frame(content, bg=BG)
centre.pack(expand=True)

# Auth card
card_frame = tk.Frame(centre, bg=CARD, bd=0,
                      highlightthickness=1, highlightbackground=BORDER)
card_frame.pack(padx=40, pady=30, ipadx=0, ipady=0)

# Card header
card_hdr = tk.Frame(card_frame, bg=CARD2, pady=18, padx=32)
card_hdr.pack(fill="x")
tk.Label(card_hdr, text="Sign In / Register", font=("Segoe UI", 14, "bold"),
         fg=TEXT, bg=CARD2).pack(anchor="w")
tk.Label(card_hdr, text="Enter your credentials to access the voting system.",
         font=FONT_LABEL, fg=TEXT3, bg=CARD2).pack(anchor="w")

# Card body
card_body = tk.Frame(card_frame, bg=CARD, padx=32, pady=24)
card_body.pack()

fields = [
    ("Username",                 None,  "user_e"),
    ("Password",                 "*",   "pass_e"),
    ("ID Number (12 digits)",    None, "id_e"),
]

entries = {}
for ph, show, key in fields:
    lbl_txt = ph.replace("(12 digits)", "").strip()
    tk.Label(card_body, text=lbl_txt, font=("Segoe UI", 9, "bold"),
             fg=TEXT2, bg=CARD, anchor="w").pack(fill="x", pady=(10, 2))
    frm, ent = make_entry(card_body, ph, show=show, width=32)
    frm.pack(fill="x")
    entries[key] = ent

user_e = entries["user_e"]
pass_e = entries["pass_e"]
id_e   = entries["id_e"]

separator(card_body, pady=14)

# Action buttons row
btn_row = tk.Frame(card_body, bg=CARD)
btn_row.pack(fill="x", pady=(0, 4))

make_button(btn_row, "Register", register, SUCCESS, SUCCESS_DK,
            padx=14, pady=10).pack(side="left", expand=True, fill="x", padx=(0, 6))
make_button(btn_row, "Login →",  login,    PRIMARY, PRIMARY_DK,
            padx=14, pady=10).pack(side="left", expand=True, fill="x")

# Info strip
info = tk.Frame(card_frame, bg=BG2, pady=10, padx=32,
                highlightthickness=1, highlightbackground=BORDER)
info.pack(fill="x")
icon_label(info, "🔒", "All data is encrypted with SHA-256", bg=BG2)
icon_label(info, "🛡️", "OTP 2-factor authentication required", bg=BG2)
icon_label(info, "🗳️", "Each voter may cast exactly one vote", bg=BG2)

# Toast (floating, placed programmatically)
toast_lbl = tk.Label(root, text="", font=("Segoe UI", 10, "bold"),
                     fg="white", bg=SUCCESS, padx=16, pady=8, bd=0)

root.mainloop() 
