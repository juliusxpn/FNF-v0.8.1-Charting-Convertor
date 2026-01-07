import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

class FNFChartConverter:
    def __init__(self):
        self.source_data = None
        self.target_data = {}
        self.available_difficulties = []

    def load(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            self.source_data = json.load(f)
        self._detect_difficulties()

    def _detect_difficulties(self):
        self.available_difficulties = []
        if not self.source_data:
            return
        
        raw_notes = self.source_data.get("notes", {})
        
        if isinstance(raw_notes, dict):
            for diff in ["easy", "normal", "hard"]:
                if diff in raw_notes and len(raw_notes[diff]) > 0:
                    self.available_difficulties.append(diff)
        else:
            seen = set()
            for note in raw_notes:
                diff = note.get("difficulty", "normal")
                if diff not in seen:
                    seen.add(diff)
                    self.available_difficulties.append(diff)

    def _build_metadata(self, difficulty: str, custom_bpm: float = None, custom_name: str = None, 
                       custom_player1: str = None, custom_player2: str = None, custom_gf: str = None,
                       custom_stage: str = None, custom_speed: float = None):
        src = self.source_data or {}
        song = {}

        song["song"] = custom_name if custom_name else src.get("song", "Unknown Song")
        song["bpm"] = custom_bpm if custom_bpm else src.get("bpm", 100)
        song["player1"] = custom_player1 if custom_player1 else src.get("player1", "bf")
        song["player2"] = custom_player2 if custom_player2 else src.get("player2", "dad")
        song["gfVersion"] = custom_gf if custom_gf else src.get("gfVersion", "gf")
        song["stage"] = custom_stage if custom_stage else src.get("stage", "stage")

        if custom_speed is not None:
            song["speed"] = custom_speed
        else:
            scroll_speed = src.get("scrollSpeed", 1.0)
            if isinstance(scroll_speed, dict):
                song["speed"] = scroll_speed.get(difficulty, scroll_speed.get("normal", 1.0))
            else:
                song["speed"] = scroll_speed

        song["needsVoices"] = True
        song["validScore"] = True
        song["sectionLengths"] = []
        song["arrowSkin"] = src.get("arrowSkin", "")
        song["splashSkin"] = src.get("splashSkin", "noteSplashes")
        song["events"] = src.get("events", [])
        song["notes"] = []

        self.target_data = {"song": song}

    def _convert_notes(self, difficulty: str, custom_bpm: float = None):
        src = self.source_data or {}
        bpm = custom_bpm if custom_bpm else src.get("bpm", 100)

        raw_notes = src.get("notes", {})
        if isinstance(raw_notes, dict):
            notes = raw_notes.get(difficulty, [])
        else:
            notes = [n for n in raw_notes if n.get("difficulty", "normal") == difficulty]

        if not notes:
            return []

        ms_per_beat = 60000 / bpm
        ms_per_step = ms_per_beat / 4
        ms_per_section = ms_per_step * 16

        def snap(t):
            return round(t / ms_per_step) * ms_per_step

        sections = {}
        section_sides = {}

        for n in notes:
            t_raw = n.get("t")
            if t_raw is None:
                continue
            t = snap(t_raw)
            d = int(n.get("d", 0))
            l = int(n.get("l", 0))
            lane = d % 4

            sec_idx = int(t // ms_per_section)
            sections.setdefault(sec_idx, []).append([int(t), lane, l])
            
            if sec_idx not in section_sides:
                section_sides[sec_idx] = {"player": 0, "opponent": 0}
            
            if d >= 4:
                section_sides[sec_idx]["player"] += 1
            else:
                section_sides[sec_idx]["opponent"] += 1

        if not sections:
            return []

        max_idx = max(sections.keys())
        kade_sections = []
        for i in range(max_idx + 1):
            sn = sections.get(i, [])
            
            must_hit = False
            if i in section_sides:
                must_hit = section_sides[i]["opponent"] > section_sides[i]["player"]
            
            kade_sections.append({
                "mustHitSection": must_hit,
                "typeOfSection": 0,
                "lengthInSteps": 16,
                "sectionNotes": sn,
                "bpm": bpm,
                "changeBPM": False
            })
        return kade_sections

    def convert_file(self, source_path: str, output_dir: str, difficulty: str = "normal", 
                    custom_bpm: float = None, custom_name: str = None, custom_player1: str = None,
                    custom_player2: str = None, custom_gf: str = None, custom_stage: str = None,
                    custom_speed: float = None) -> str:
        self.load(source_path)
        
        if difficulty not in self.available_difficulties:
            raise ValueError(f"Difficulty '{difficulty}' has no notes in this chart")
        
        self._build_metadata(difficulty, custom_bpm, custom_name, custom_player1, custom_player2, 
                           custom_gf, custom_stage, custom_speed)
        self.target_data["song"]["notes"] = self._convert_notes(difficulty, custom_bpm)

        src_name = Path(source_path).stem
        out_name = f"{src_name}-{difficulty}" if difficulty != "normal" else src_name
        out_path = os.path.join(output_dir, f"{out_name}.json")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.target_data, f, indent=4)
        return out_path


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command=None, bg_color='#c586c0', hover_color='#d8a0d0', 
                 text_color='#ffffff', font=('Segoe UI', 10), width=100, height=40, corner_radius=8):
        super().__init__(parent, width=width, height=height, bg=parent['bg'], highlightthickness=0)
        
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.corner_radius = corner_radius
        self.text = text
        self.font = font
        
        self._draw_button(bg_color)
        
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _draw_button(self, color):
        self.delete("all")
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        
        self.create_arc(0, 0, self.corner_radius*2, self.corner_radius*2, 
                       start=90, extent=90, fill=color, outline=color)
        self.create_arc(width-self.corner_radius*2, 0, width, self.corner_radius*2, 
                       start=0, extent=90, fill=color, outline=color)
        self.create_arc(0, height-self.corner_radius*2, self.corner_radius*2, height, 
                       start=180, extent=90, fill=color, outline=color)
        self.create_arc(width-self.corner_radius*2, height-self.corner_radius*2, 
                       width, height, start=270, extent=90, fill=color, outline=color)
        
        self.create_rectangle(self.corner_radius, 0, width-self.corner_radius, height, 
                            fill=color, outline=color)
        self.create_rectangle(0, self.corner_radius, width, height-self.corner_radius, 
                            fill=color, outline=color)
        
        self.create_text(width/2, height/2, text=self.text, fill=self.text_color, font=self.font)
    
    def _on_enter(self, event):
        self._draw_button(self.hover_color)
        self.config(cursor='hand2')
    
    def _on_leave(self, event):
        self._draw_button(self.bg_color)
        self.config(cursor='')
    
    def _on_click(self, event):
        if self.command:
            self.command()


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg_color, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg_color)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.scrollable_frame.bind("<Enter>", self._bind_mousewheel)
        self.scrollable_frame.bind("<Leave>", self._unbind_mousewheel)
        
        for child in self.scrollable_frame.winfo_children():
            child.bind("<Enter>", self._bind_mousewheel)
            child.bind("<Leave>", self._unbind_mousewheel)
    
    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)
    
    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")
    
    def _on_mousewheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")


class ConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Vesta's Convertor (v0.1.0)")
        self.root.geometry("1200x00")
        self.root.minsize(200, 650)
        
        self.colors = {
            'bg_dark': '#1e1e1e',
            'bg_medium': '#252526',
            'bg_light': '#2d2d30',
            'accent': '#c586c0',
            'accent_hover': '#d8a0d0',
            'text': '#cccccc',
            'text_dim': '#858585',
            'border': '#3e3e42',
            'input_bg': '#3c3c3c',
            'button': '#c586c0',
            'button_hover': '#d8a0d0',
            'disabled': '#4a4a4a'
        }
        
        self.source_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.selected_difficulty = tk.StringVar(value="normal")
        self.custom_bpm = tk.StringVar()
        self.custom_name = tk.StringVar()
        self.custom_player1 = tk.StringVar()
        self.custom_player2 = tk.StringVar()
        self.custom_gf = tk.StringVar()
        self.custom_stage = tk.StringVar()
        self.custom_speed = tk.StringVar()
        
        self.converter = FNFChartConverter()
        self.difficulty_buttons = {}
        
        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Dark.TFrame', background=self.colors['bg_dark'])
        style.configure('Medium.TFrame', background=self.colors['bg_medium'])
        style.configure('Light.TFrame', background=self.colors['bg_light'])

    def _build_ui(self):
        self.root.configure(bg=self.colors['bg_dark'])
        
        self._create_header()
        self._create_main_content()

    def _create_header(self):
        header = tk.Frame(self.root, bg=self.colors['bg_medium'], height=70)
        header.pack(fill='x', padx=0, pady=0)
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header,
            text="THE MOST ASS CONVERTOR EVER (Vesta's Convertor v0.1.0)",
            font=('Segoe UI', 18, 'bold'),
            fg=self.colors['text'],
            bg=self.colors['bg_medium']
        )
        title_label.pack(side='left', padx=20, pady=20)
        
        version_label = tk.Label(
            header,
            text="v0.8.1 -> Kade Engine",
            font=('Segoe UI', 10),
            fg=self.colors['accent'],
            bg=self.colors['bg_medium']
        )
        version_label.pack(side='left', padx=5, pady=20)

    def _create_main_content(self):
        main = tk.Frame(self.root, bg=self.colors['bg_dark'])
        main.pack(fill='both', expand=True, padx=20, pady=20)
        
        left_panel = tk.Frame(main, bg=self.colors['bg_medium'], width=420)
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        right_panel = tk.Frame(main, bg=self.colors['bg_medium'], width=420)
        right_panel.pack(side='right', fill='both', expand=True, padx=(10, 0))
        right_panel.pack_propagate(False)
        
        self._create_file_selection(left_panel)
        self._create_metadata_inputs(right_panel)

    def _create_file_selection(self, parent):
        tk.Label(
            parent,
            text="Main",
            font=('Segoe UI', 12, 'bold'),
            fg=self.colors['accent'],
            bg=self.colors['bg_medium']
        ).pack(anchor='w', padx=20, pady=(20, 15))

        
        source_frame = tk.Frame(parent, bg=self.colors['bg_light'], bd=0)
        source_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        tk.Label(
            source_frame,
            text="FNF v0.8.1 Chart file (.json)",
            font=('Segoe UI', 9),
            fg=self.colors['text_dim'],
            bg=self.colors['bg_light']
        ).pack(anchor='w', padx=15, pady=(10, 5))
        
        
        source_entry_frame = tk.Frame(source_frame, bg=self.colors['bg_light'])
        source_entry_frame.pack(fill='x', padx=15, pady=(0, 10))
        
        source_entry = tk.Entry(
            source_entry_frame,
            textvariable=self.source_path,
            font=('Consolas', 9),
            fg=self.colors['text'],
            bg=self.colors['input_bg'],
            insertbackground=self.colors['text'],
            relief='flat',
            bd=0
        )
        source_entry.pack(side='left', fill='x', expand=True, ipady=8, padx=(0, 10))
        
        source_btn = RoundedButton(
            source_entry_frame,
            text="Browse",
            command=self.browse_source,
            bg_color=self.colors['button'],
            hover_color=self.colors['button_hover'],
            font=('Segoe UI', 9),
            width=80,
            height=34,
            corner_radius=6
        )
        source_btn.pack(side='right')
        
        output_frame = tk.Frame(parent, bg=self.colors['bg_light'], bd=0)
        output_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        tk.Label(
            output_frame,
            text="Output folder (where the converted file will be at)",
            font=('Segoe UI', 9),
            fg=self.colors['text_dim'],
            bg=self.colors['bg_light']
        ).pack(anchor='w', padx=15, pady=(10, 5))
        
        output_entry_frame = tk.Frame(output_frame, bg=self.colors['bg_light'])
        output_entry_frame.pack(fill='x', padx=15, pady=(0, 10))
        
        output_entry = tk.Entry(
            output_entry_frame,
            textvariable=self.output_dir,
            font=('Consolas', 9),
            fg=self.colors['text'],
            bg=self.colors['input_bg'],
            insertbackground=self.colors['text'],
            relief='flat',
            bd=0
        )
        output_entry.pack(side='left', fill='x', expand=True, ipady=8, padx=(0, 10))
        
        output_btn = RoundedButton(
            output_entry_frame,
            text="Browse",
            command=self.browse_output,
            bg_color=self.colors['button'],
            hover_color=self.colors['button_hover'],
            font=('Segoe UI', 9),
            width=80,
            height=34,
            corner_radius=6
        )
        output_btn.pack(side='right')
        
        tk.Label(
            parent,
            text="Difficulty",
            font=('Segoe UI', 12, 'bold'),
            fg=self.colors['accent'],
            bg=self.colors['bg_medium']
        ).pack(anchor='w', padx=20, pady=(15, 15))

        tk.Label(
            parent,
            text="Choose song difficulty, empty ones will be filtered out.",
            font=('Segoe UI', 8),
            fg=self.colors['text_dim'],
            bg=self.colors['bg_medium']
        ).pack(anchor='w', padx=20, pady=(0, 15))
        
        diff_container = tk.Frame(parent, bg=self.colors['bg_light'])
        diff_container.pack(fill='x', padx=20, pady=(0, 20))
        
        self.diff_frame = tk.Frame(diff_container, bg=self.colors['bg_light'])
        self.diff_frame.pack(pady=15, padx=15)
        
        self._create_difficulty_buttons()
        
        convert_frame = tk.Frame(parent, bg=self.colors['bg_medium'])
        convert_frame.pack(fill='x', padx=20, pady=(20, 20))
        
        convert_btn = RoundedButton(
            convert_frame,
            text="Convert the funny chart",
            command=self.perform_conversion,
            bg_color=self.colors['accent'],
            hover_color=self.colors['accent_hover'],
            font=('Segoe UI', 13, 'bold'),
            width=360,
            height=50,
            corner_radius=8
        )
        convert_btn.pack(fill='x')

    def _create_difficulty_buttons(self):
        for widget in self.diff_frame.winfo_children():
            widget.destroy()
        
        self.difficulty_buttons.clear()
        
        for diff in ["easy", "normal", "hard"]:
            rb = tk.Radiobutton(
                self.diff_frame,
                text=diff.upper(),
                value=diff,
                variable=self.selected_difficulty,
                font=('Segoe UI', 10, 'bold'),
                fg=self.colors['text_dim'],
                bg=self.colors['bg_light'],
                selectcolor=self.colors['accent'],
                activebackground=self.colors['bg_light'],
                activeforeground=self.colors['text'],
                cursor='hand2',
                indicatoron=True,
                state='disabled'
            )
            rb.pack(side='left', padx=15)
            self.difficulty_buttons[diff] = rb

    def _update_difficulty_buttons(self, available_diffs):
        for diff, button in self.difficulty_buttons.items():
            if diff in available_diffs:
                button.config(
                    state='normal',
                    fg=self.colors['text'],
                    cursor='hand2'
                )
            else:
                button.config(
                    state='disabled',
                    fg=self.colors['text_dim'],
                    cursor='arrow'
                )
        
        if available_diffs:
            self.selected_difficulty.set(available_diffs[0])

    def _create_metadata_inputs(self, parent):
        header_frame = tk.Frame(parent, bg=self.colors['bg_medium'])
        header_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        tk.Label(
            header_frame,
            text="Charting Data",
            font=('Segoe UI', 12, 'bold'),
            fg=self.colors['accent'],
            bg=self.colors['bg_medium']
        ).pack(anchor='w')
        
        tk.Label(
            parent,
            text="Input your song bpm, name, etc right in here.",
            font=('Segoe UI', 8),
            fg=self.colors['text_dim'],
            bg=self.colors['bg_medium']
        ).pack(anchor='w', padx=20, pady=(0, 15))
        
        scrollable = ScrollableFrame(parent, bg_color=self.colors['bg_medium'])
        scrollable.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        inputs = [
            ("Song Name", self.custom_name),
            ("BPM (Beats Per Minute)", self.custom_bpm),
            ("Scroll Speed", self.custom_speed),
            ("Player 1 (bf)", self.custom_player1),
            ("Player 2 (dad)", self.custom_player2),
            ("Player 3 (gf)", self.custom_gf),
            ("Stage", self.custom_stage)
        ]
        
        for label_text, var in inputs:
            self._create_input_field(scrollable.scrollable_frame, label_text, var)

    def _create_input_field(self, parent, label_text, variable):
        container = tk.Frame(parent, bg=self.colors['bg_light'])
        container.pack(fill='x', padx=0, pady=(0, 12))
        
        tk.Label(
            container,
            text=label_text,
            font=('Segoe UI', 9),
            fg=self.colors['text_dim'],
            bg=self.colors['bg_light']
        ).pack(anchor='w', padx=15, pady=(8, 4))
        
        entry = tk.Entry(
            container,
            textvariable=variable,
            font=('Segoe UI', 10),
            fg=self.colors['text'],
            bg=self.colors['input_bg'],
            insertbackground=self.colors['text'],
            relief='flat',
            bd=0
        )
        entry.pack(fill='x', padx=15, pady=(0, 8), ipady=6)

    def browse_source(self):
        path = filedialog.askopenfilename(
            title="Select FNF v0.8.1 Chart",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            self.source_path.set(path)
            try:
                self.converter.load(path)
                
                available = self.converter.available_difficulties
                if not available:
                    messagebox.showwarning(
                        "Convertor Error...",
                        "The chosen charting doesn't have any difficulties."
                    )
                    return
                
                self._update_difficulty_buttons(available)
                
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                note_counts = {}
                raw_notes = data.get("notes", {})
                if isinstance(raw_notes, dict):
                    for diff in ["easy", "normal", "hard"]:
                        if diff in raw_notes:
                            note_counts[diff] = len(raw_notes[diff])
                
                info = "Loaded the selected chart, here is data from it:\n\n"
                info += f"Song: {data.get('song', 'Not for avail. (N/F/A)')}\n"
                info += f"BPM: {data.get('bpm', 'Not for avail. (N/F/A)')}\n"
                info += f"Player 1: {data.get('player1', 'Not for avail. (N/F/A)')}\n"
                info += f"Player 2: {data.get('player2', 'Not for avail. (N/F/A)')}\n"
                info += f"GF: {data.get('gfVersion', 'Not for avail. (N/F/A)')}\n"
                info += f"Stage: {data.get('stage', 'Not for avail. (N/F/A)')}\n"
                info += f"Scroll Speed: {data.get('scrollSpeed', 'Not for avail. (N/F/A)')}\n\n"
                info += "Available difficulties:\n"
                for diff in available:
                    count = note_counts.get(diff, 0)
                    info += f"• {diff.lower()}: {count} notes\n"
                
                messagebox.showinfo("Chart Loaded", info)
                
            except Exception as e:
                messagebox.showerror("Convertor Error...", f"Failed to load chart:\n\n{str(e)}")

    def browse_output(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_dir.set(path)

    def perform_conversion(self):
        if not self.source_path.get():
            messagebox.showwarning("Convertor Error...", "Select an VALID source chart file.")
            return
        if not self.output_dir.get():
            messagebox.showwarning("Convertor Error...", "Select an VALID output folder.")
            return

        custom_bpm = None
        if self.custom_bpm.get().strip():
            try:
                custom_bpm = float(self.custom_bpm.get())
                if custom_bpm <= 0:
                    messagebox.showerror("Convertor Error...", "BPM must be positive (why is this even a error? TBH I don't know, im bored.)")
                    return
            except ValueError:
                messagebox.showerror("Convertor Error...", "Please enter a valid number for BPM")
                return

        custom_speed = None
        if self.custom_speed.get().strip():
            try:
                custom_speed = float(self.custom_speed.get())
                if custom_speed <= 0:
                    messagebox.showerror("Convertor Error...", "Scroll speed must be positive (again, idk why i keep making stupid errors like these, but sure)")
                    return
            except ValueError:
                messagebox.showerror("Convertor Error...", "Please enter a valid number for scroll speed")
                return

        custom_name = self.custom_name.get().strip() or None
        custom_player1 = self.custom_player1.get().strip() or None
        custom_player2 = self.custom_player2.get().strip() or None
        custom_gf = self.custom_gf.get().strip() or None
        custom_stage = self.custom_stage.get().strip() or None

        selected_diff = self.selected_difficulty.get()
        if selected_diff not in self.converter.available_difficulties:
            messagebox.showerror(
                "Convertor Error...",
                f"The selected difficulty '{selected_diff}' has no notes in this chart"
            )
            return

        self.root.update()

        try:
            out_path = self.converter.convert_file(
                self.source_path.get(),
                self.output_dir.get(),
                selected_diff,
                custom_bpm,
                custom_name,
                custom_player1,
                custom_player2,
                custom_gf,
                custom_stage,
                custom_speed
            )
            messagebox.showinfo(
                "Conversion Complete :coffetni:",
                f"Chart converted successfully! =D\n\nDifficulty: {selected_diff.upper()}\nSaved to:\n{out_path}"
            )
        except Exception as e:
            messagebox.showerror("Convertor Error...", f"Failed to convert chart:\n\n{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ConverterApp(root)
    root.mainloop() # LOL LINE "699" SO FUNNY AND HILARIOUS
