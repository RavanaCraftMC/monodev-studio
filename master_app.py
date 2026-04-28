import os
import threading
import requests
import cv2
from PIL import Image
import customtkinter as ctk
from elevenlabs.client import ElevenLabs
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip, afx

# ==========================================
# 1. THE PRO GUI APPLICATION
# ==========================================
class MonoDevShortsCreator(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MonoDev's Automated Shorts Creator v1.0")
        self.geometry("1100x750")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # --- GRID LAYOUT ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # LEFT SIDEBAR: SETTINGS & API
        # ==========================================
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="MonoDev\nStudio", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        ctk.CTkLabel(self.sidebar_frame, text="API Configuration", font=ctk.CTkFont(size=14, weight="bold"), text_color="gray").grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.eleven_key_input = ctk.CTkEntry(self.sidebar_frame, placeholder_text="ElevenLabs API Key", show="*")
        self.eleven_key_input.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="ew")
        
        self.pexels_key_input = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Pexels API Key", show="*")
        self.pexels_key_input.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")

        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="System Ready", text_color="#00FF00", font=ctk.CTkFont(weight="bold"))
        self.status_label.grid(row=4, column=0, padx=20, pady=10)

        # ==========================================
        # CENTER PANEL: CREATION ENGINE
        # ==========================================
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Top section: Script & Keywords
        self.input_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.input_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")

        ctk.CTkLabel(self.input_frame, text="1. The Script", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        self.script_input = ctk.CTkTextbox(self.input_frame, height=120)
        self.script_input.pack(fill="x", pady=(5, 15))
        self.script_input.insert("1.0", "Welcome to the channel! Today we are looking at beautiful landscapes.")

        ctk.CTkLabel(self.input_frame, text="2. Visual Theme (Pexels Keyword)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        self.keyword_input = ctk.CTkEntry(self.input_frame, height=40)
        self.keyword_input.pack(fill="x", pady=(5, 20))
        self.keyword_input.insert("0", "landscape")

        self.generate_btn = ctk.CTkButton(self.input_frame, text="RENDER SHORT", font=ctk.CTkFont(size=16, weight="bold"), height=50, command=self.start_generation)
        self.generate_btn.pack(fill="x")

        self.progress_bar = ctk.CTkProgressBar(self.input_frame)
        self.progress_bar.pack(fill="x", pady=(15, 0))
        self.progress_bar.set(0)

        # Bottom section: Metadata Tabview
        self.metadata_tab = ctk.CTkTabview(self.main_frame)
        self.metadata_tab.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.metadata_tab.add("YouTube Metadata")

        ctk.CTkLabel(self.metadata_tab.tab("YouTube Metadata"), text="Optimized Title").pack(anchor="w", padx=10, pady=(5,0))
        self.title_input = ctk.CTkEntry(self.metadata_tab.tab("YouTube Metadata"))
        self.title_input.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(self.metadata_tab.tab("YouTube Metadata"), text="Description & Credits").pack(anchor="w", padx=10)
        self.desc_input = ctk.CTkTextbox(self.metadata_tab.tab("YouTube Metadata"), height=100)
        self.desc_input.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ctk.CTkLabel(self.metadata_tab.tab("YouTube Metadata"), text="Viral Tags").pack(anchor="w", padx=10)
        self.tags_input = ctk.CTkEntry(self.metadata_tab.tab("YouTube Metadata"))
        self.tags_input.pack(fill="x", padx=10, pady=(0, 10))

        # ==========================================
        # RIGHT PANEL: VIDEO PREVIEW
        # ==========================================
        self.preview_frame = ctk.CTkFrame(self, width=380, corner_radius=10)
        self.preview_frame.grid(row=0, column=2, padx=(0, 15), pady=15, sticky="nsew")
        self.preview_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.preview_frame, text="Live Preview", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, pady=20)
        
        self.video_screen = ctk.CTkLabel(self.preview_frame, text="NO MEDIA", width=360, height=640, fg_color="black", corner_radius=10)
        self.video_screen.grid(row=1, column=0, padx=10, sticky="n")

        self.play_btn = ctk.CTkButton(self.preview_frame, text="▶ Play Final Video", state="disabled", command=self.play_video)
        self.play_btn.grid(row=2, column=0, pady=20, padx=20, sticky="ew")

        self.cap = None

    # ==========================================
    # LOGIC ENGINE
    # ==========================================
    def update_status(self, text, color="#00FF00", progress=0.0):
        self.status_label.configure(text=text, text_color=color)
        self.progress_bar.set(progress)

    def start_generation(self):
        # API Check before starting
        if not self.eleven_key_input.get() or not self.pexels_key_input.get():
            self.update_status("ERROR: Missing API Keys!", color="red", progress=0)
            return

        self.generate_btn.configure(state="disabled", text="RENDERING...")
        threading.Thread(target=self.build_video_logic).start()

    def build_video_logic(self):
        script_text = self.script_input.get("1.0", "end-1c").strip()
        search_keyword = self.keyword_input.get().strip()
        eleven_key = self.eleven_key_input.get().strip()
        pexels_key = self.pexels_key_input.get().strip()

        try:
            # --- STEP A: Fetch Audio ---
            self.update_status("Fetching Voiceover...", progress=0.2)
            try:
                client = ElevenLabs(api_key=eleven_key)
                audio_stream = client.text_to_speech.convert(
                    text=script_text,
                    voice_id="SCbIlR40EEyW2I6quW1h", 
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128"
                )
                with open("voiceover.mp3", "wb") as f:
                    for chunk in audio_stream:
                        if chunk: f.write(chunk)
            except Exception:
                raise Exception("ElevenLabs Error. Check API Key.")

            # --- STEP B: Fetch Images ---
            self.update_status("Downloading Assets...", progress=0.4)
            try:
                headers = {"Authorization": pexels_key}
                url = f"https://api.pexels.com/v1/search?query={search_keyword}&per_page=5&orientation=portrait"
                response = requests.get(url, headers=headers)
                
                if response.status_code != 200:
                    raise Exception("Invalid Pexels API Key!")
                    
                response_data = response.json()
                if not response_data.get('photos'):
                    raise Exception(f"No photos found for '{search_keyword}'")
                
                credits_list = ["--- VIDEO CREDITS ---", "Voiceover generated by elevenlabs.io\n", "Visuals provided by Pexels:"]
                
                for i, photo in enumerate(response_data.get('photos', [])):
                    img_data = requests.get(photo['src']['large2x']).content
                    with open(f"image_{i}.jpg", 'wb') as handler:
                        handler.write(img_data)
                    credits_list.append(f"- Photo by {photo['photographer']}: {photo['photographer_url']}")
            except Exception as e:
                raise Exception(f"Pexels Error: {str(e)}")

            # --- STEP C: Render Video ---
            self.update_status("Compositing Video Engine...", progress=0.6)
            
            voice_audio = AudioFileClip("voiceover.mp3")
            audio_dur = voice_audio.duration
            
            if os.path.exists("music.mp3"):
                ambient = AudioFileClip("music.mp3").volumex(0.08) 
                ambient = afx.audio_loop(ambient, duration=audio_dur) 
                final_audio = CompositeAudioClip([ambient, voice_audio])
            else:
                final_audio = voice_audio
            
            image_files = [f"image_{i}.jpg" for i in range(5) if os.path.exists(f"image_{i}.jpg")]
            time_per_image = audio_dur / len(image_files)
            
            bg_clips = [ImageClip(img).set_duration(time_per_image).resize(width=720, height=1280) for img in image_files]
            
            final_video = concatenate_videoclips(bg_clips, method="compose")
            final_video = final_video.set_audio(final_audio)
            
            self.update_status("Exporting .MP4 (This takes time)...", progress=0.8)
            final_video.write_videofile(
                "final_video.mp4", 
                fps=24, 
                codec="mpeg4",                    
                bitrate="8000k",                  
                audio_codec="aac",                
                temp_audiofile="temp-audio.m4a",  
                remove_temp=True,                 
                logger=None
            )

            # --- STEP D: Update GUI ---
            self.update_status("RENDER COMPLETE!", color="#00FF00", progress=1.0)
            self.generate_btn.configure(state="normal", text="RENDER SHORT")
            self.play_btn.configure(state="normal")
            
            self.title_input.delete("0", "end")
            self.title_input.insert("0", f"Amazing {search_keyword.title()} Facts! #shorts")
            
            self.desc_input.delete("1.0", "end")
            full_desc = f"Check out this awesome video about {search_keyword}!\n\n" + "\n".join(credits_list)
            self.desc_input.insert("1.0", full_desc)
            
            self.tags_input.delete("0", "end")
            self.tags_input.insert("0", f"{search_keyword}, facts, shorts, viral")

        except Exception as e:
            self.update_status(str(e), color="red", progress=0)
            self.generate_btn.configure(state="normal", text="RENDER SHORT")

    # ==========================================
    # PREVIEW PLAYER
    # ==========================================
    def play_video(self):
        self.play_btn.configure(state="disabled")
        self.cap = cv2.VideoCapture("final_video.mp4")
        self.update_frame()

    def update_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(360, 640))
                
                self.video_screen.configure(image=ctk_img, text="")
                self.video_screen.image = ctk_img 
                
                self.after(40, self.update_frame)
            else:
                self.cap.release()
                self.play_btn.configure(state="normal")

if __name__ == "__main__":
    app = MonoDevShortsCreator()
    app.mainloop()