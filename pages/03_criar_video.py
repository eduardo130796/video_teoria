import os
from moviepy.editor import (
    AudioFileClip, ImageClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip
)
from moviepy.audio.AudioClip import AudioArrayClip
from PIL import Image
import re
import numpy as np
import streamlit as st
import io
import tempfile
import time

def pil_to_npimage(pil_image):
    return np.array(pil_image)

def create_silent_audio_clip(duration, fps=44100):
    silent_array = np.zeros((int(fps * duration), 2))
    return AudioArrayClip(silent_array, fps=fps)

def create_slide(slide_path, audio_paths, audio_delay, extra_duration, fade_duration=0.2, additional_silent_time=1):
    # Carrega a imagem e prepara o clipe de imagem
    image_np = pil_to_npimage(Image.open(slide_path))
    total_audio_duration = sum([AudioFileClip(audio).duration for audio in audio_paths])
    slide_duration = total_audio_duration + audio_delay + extra_duration + additional_silent_time
    slide_clip = ImageClip(image_np, duration=slide_duration)

    # Criar um clipe de áudio silencioso para o atraso
    silent_clip = create_silent_audio_clip(audio_delay)

    # Carregar clipes de áudio, aplicar fade in e fade out
    audio_clips = [silent_clip] + [AudioFileClip(audio).audio_fadein(fade_duration).audio_fadeout(fade_duration) for audio in audio_paths]
    combined_audio_clip = concatenate_audioclips(audio_clips)

    # Configurar o áudio para começar após o extra_duration
    final_audio_clip = CompositeAudioClip([combined_audio_clip.set_start(extra_duration)])
    slide_clip = slide_clip.set_audio(final_audio_clip)

    return slide_clip



def streamlit_app():
    st.title("Gerador de Vídeo de Slides")

    uploaded_images = st.file_uploader("Envie as imagens dos slides", type=['jpg', 'png'], accept_multiple_files=True)
    uploaded_audios = st.file_uploader("Envie os áudios", type=['mp3'], accept_multiple_files=True)

    output_file_name = st.text_input("Nome do vídeo", "video_gerado")

    if st.button("Criar Vídeo"):
        if uploaded_images and uploaded_audios:
            with st.spinner("Gerando vídeo..."), tempfile.TemporaryDirectory() as temp_dir:
                progress_bar = st.progress(0)
                status_text = st.empty()
                start_time = time.time()

                audio_paths = {}
                for audio in uploaded_audios:
                    audio_path = os.path.join(temp_dir, audio.name)
                    audio_paths[audio.name] = audio_path
                    with open(audio_path, 'wb') as file:
                        file.write(audio.getbuffer())

                video_clips = []
                total_steps = len(uploaded_images) + 1
                for i, img in enumerate(uploaded_images):
                    image = Image.open(io.BytesIO(img.getvalue()))
                    slide_path = os.path.join(temp_dir, img.name)
                    image.save(slide_path)

                    slide_number = re.match(r'Slide(\d+)', img.name, re.IGNORECASE).group(1)
                    audio_pattern = rf'{slide_number}\.[0-9]+_narracao_slide\.mp3'
                    slide_audio_paths = [audio_paths[audio] for audio in audio_paths if re.match(audio_pattern, audio)]

                    audio_clips = [AudioFileClip(audio) for audio in slide_audio_paths]
                    video_clips.append(create_slide(slide_path, slide_audio_paths, 0.5, 0.5))

                    # Fechar clipes de áudio após uso
                    for audio_clip in audio_clips:
                        audio_clip.close()
                    # Atualização da barra de progresso e do status
                    elapsed_time = time.time() - start_time
                    progress = (i + 1) / total_steps
                    progress_bar.progress(progress)

                    status_text.text(f"Processando Slide {i+1}/{len(uploaded_images)} ({elapsed_time:.2f}s)")

                    # Fechar clipes de áudio após uso
                    for audio_clip in audio_clips:
                        audio_clip.close()
                    
                    video_clips.append(create_slide(slide_path, slide_audio_paths, 0.5, 0.5))

                    
                status_text.text("Finalizando a criação do vídeo...")
                # Concatenar clipes
                final_clips = [video_clips[0]]
                transition_duration = 0.5  # Duração da transição crossfade

                # Adicionar transições de crossfade
                for clip in video_clips[1:]:
                    clip = clip.crossfadein(transition_duration)
                    final_clips.append(clip)

                final_video = concatenate_videoclips(final_clips, method="compose", padding=-transition_duration)
                output_path = os.path.join(temp_dir, f"{output_file_name}.mp4")
                final_video.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=24)

                # Atualização final da barra de progresso e do status
                total_time = time.time() - start_time
                progress_bar.progress(1.0)
                status_text.text(f"Vídeo gerado com sucesso em {total_time:.2f} segundos.")

                status_text.text("Vídeo gerado com sucesso!")

                # Garantir que os arquivos sejam fechados antes da exclusão
                del video_clips
                del final_video

                # Download do vídeo gerado
                with open(output_path, 'rb') as file:
                    st.download_button(
                        label="Baixar Vídeo Gerado",
                        data=file,
                        file_name=f"{output_file_name}.mp4",
                        mime="video/mp4"
                    )

                st.success("Vídeo gerado com sucesso!")

if __name__ == "__main__":
    streamlit_app()