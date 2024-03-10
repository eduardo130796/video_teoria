import os
from moviepy.editor import (
    AudioFileClip, ImageClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip
)
from moviepy.audio.AudioClip import AudioArrayClip
from PIL import Image
import numpy as np
import streamlit as st
import io
import time
import re

def pil_to_npimage(pil_image):
    """Convert PIL Image to numpy array."""
    return np.array(pil_image)

def create_silent_audio_clip(duration, fps=44100):
    """Create a silent audio clip with given duration and fps."""
    silent_array = np.zeros((int(fps * duration), 2))
    return AudioArrayClip(silent_array, fps=fps)

def create_slide(slide_path, audio_paths, audio_delay, extra_duration, fade_duration=0.2, additional_silent_time=1):
    """Create a video slide with given parameters."""
    # Load the image and prepare the image clip
    image_np = pil_to_npimage(Image.open(slide_path))
    total_audio_duration = sum([AudioFileClip(audio).duration for audio in audio_paths])
    slide_duration = total_audio_duration + audio_delay + extra_duration + additional_silent_time
    slide_clip = ImageClip(image_np, duration=slide_duration)

    # Create a silent audio clip for the delay
    silent_clip = create_silent_audio_clip(audio_delay)

    # Load audio clips, apply fade in and fade out
    audio_clips = [silent_clip] + [
        AudioFileClip(audio).audio_fadein(fade_duration).audio_fadeout(fade_duration) 
        for audio in audio_paths
    ]
    combined_audio_clip = concatenate_audioclips(audio_clips)

    # Set up the audio to start after the extra_duration
    final_audio_clip = CompositeAudioClip([combined_audio_clip.set_start(extra_duration)])
    slide_clip = slide_clip.set_audio(final_audio_clip)

    return slide_clip

def create_fade_transition(clip, fade_duration=0.5):
    """Aplica um fade in e fade out no clipe dado."""
    return clip.fadein(fade_duration).fadeout(fade_duration)

def format_time(seconds):
    """Converte segundos em minutos e segundos."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins} minuto(s) e {secs} segundo(s)"

def streamlit_app():
    """Streamlit app for generating slideshow videos."""
    st.title("Gerador de Vídeo")

    uploaded_images = st.file_uploader("Envie as imagens dos slides", type=['jpg', 'png'], accept_multiple_files=True)
    uploaded_audios = st.file_uploader("Envie os áudios", type=['mp3'], accept_multiple_files=True)

    output_file_name = st.text_input("Nome do vídeo", "video_gerado")
    persistent_dir = os.path.join(os.getcwd(), "videos")

    if not os.path.exists(persistent_dir):
        os.makedirs(persistent_dir)

    if st.button("Criar Vídeo"):
        if uploaded_images and uploaded_audios:
            with st.spinner("Gerando vídeo..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                start_time = time.time()

                audio_paths = {}
                for audio in uploaded_audios:
                    audio_path = os.path.join(persistent_dir, audio.name)
                    audio_paths[audio.name] = audio_path
                    with open(audio_path, 'wb') as file:
                        file.write(audio.getbuffer())

                video_clips = []
                total_steps = len(uploaded_images)
                for i, img in enumerate(uploaded_images):
                    with Image.open(io.BytesIO(img.getvalue())) as image:
                        slide_path = os.path.join(persistent_dir, img.name)
                        image.save(slide_path)

                    slide_audio_pattern = rf'^{i+1}\.[0-9]+_narracao_slide\.mp3$'
                    matched_audios = [name for name in audio_paths if re.match(slide_audio_pattern, name)]
    
                    # Verifica se a correspondência foi encontrada antes de tentar acessar o elemento
                    sorted_audios = sorted(matched_audios, key=lambda x: int(re.findall(rf'^{i+1}\.([0-9]+)_narracao_slide\.mp3$', x)[0]) if re.findall(rf'^{i+1}\.([0-9]+)_narracao_slide\.mp3$', x) else 0)
    
                    slide_audio_paths = [audio_paths[name] for name in sorted_audios]
                    video_clips.append(create_slide(slide_path, slide_audio_paths, 0.3, 0.3))

                    elapsed_time = time.time() - start_time
                    progress = (i + 1) / total_steps
                    progress_bar.progress(progress)
                    status_text.text(f"Processing Slide {i+1}/{len(uploaded_images)} ({elapsed_time:.2f}s)")

                # Atualiza o status com o tempo decorrido
                elapsed_time = time.time() - start_time
                formatted_time = format_time(elapsed_time)
                status_text.text(f"Processando Slide {i+1}/{len(uploaded_images)} - Tempo decorrido: {formatted_time}")

                # Processamento dos slides com transição otimizada
                final_clips = []
                fade_duration = 0.1  # Duracao do fade in e fade out

                for clip in video_clips:
                    faded_clip = create_fade_transition(clip, fade_duration)
                    final_clips.append(faded_clip)

                final_video = concatenate_videoclips(final_clips, method="compose")
 
                output_path = os.path.join(persistent_dir, f"{output_file_name}.mp4")
                final_video.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=24)

                del video_clips
                del final_video
                total_time = time.time() - start_time
                formatted_total_time = format_time(total_time)
                status_text.text(f"Vídeo gerado com sucesso em {formatted_total_time}.")

                progress_bar.empty()

                with open(output_path, 'rb') as file:
                    st.download_button("Baixar Vídeo Gerado", file, file_name=f"{output_file_name}.mp4", mime="video/mp4")

    # Button to delete files
    if st.button("Apagar Arquivos"):
        try:
            for file in os.listdir(persistent_dir):
                os.remove(os.path.join(persistent_dir, file))
            st.success("Arquivos apagados com sucesso.")
        except Exception as e:
            st.error(f"Erro ao apagar arquivos: {e}")

if __name__ == "__main__":
    streamlit_app()
