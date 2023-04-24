import streamlit as st
import replicate
import requests
import os
import io
import base64
from PIL import Image
import numpy as np
from streamlit_cropper import st_cropper


@st.cache_data(show_spinner="Generating caption...")
def getCaption(image_bytes):
    return replicate.run(
        "methexis-inc/img2prompt:50adaf2d3ad20a6f911a8a9e3ccf777b263b8596fbd2c8fc26e8888f8a0edbb5", input={"image": image_bytes})


def renderCaption(image, image_bytes):
    caption = getCaption(image_bytes)
    mod_caption = st.text_area(
        'Below is a descriptive caption for your arther. You can modify it to generate a new image.', caption)
    if mod_caption and mod_caption != caption:
        with st.spinner('Generating your modified arther'):
            try:
              img = getImageFromImage(mod_caption, image)
              st.image(img)
            except Exception:
                st.error("Your prompt is invalid")


def renderPartModification(image, image_bytes):
    orig_image = Image.open(image_bytes)
    rect = st_cropper(
        orig_image,
        realtime_update=True,
        return_type="box"
    )
    left, top, width, height = tuple(map(int, rect.values()))

    mask = np.zeros(orig_image.size, dtype='uint8')
    mask[top:top + height, left:left + width] = 255

    # converting the mask into a byte buffer
    mask = Image.fromarray(mask)
    buf = io.BytesIO()
    mask.save(buf, format='PNG')

    mod = st.text_input(
        'How would you like to modify the selected area?', '')
    if len(mod) > 0:
        with st.spinner('Modifying your arther'):
            img = getInpaintedImage(mod, image, buf.getvalue())
            st.image(img)


def getInpaintedImage(prompt, init_image, mask):
    response = requests.post(
        f"{stability_api_host}/v1/generation/{stability_engine_id}/image-to-image/masking",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {stability_api_key}"
        },
        files={
            "init_image": init_image,
            "mask_image": mask
        },
        data={
            "mask_source": "MASK_IMAGE_WHITE",
            "text_prompts[0][text]": prompt,
            "text_prompts[0][weight]": 1,
            "cfg_scale": 7,
            "clip_guidance_preset": "FAST_BLUE",
            "samples": 1,
            "steps": 30,
        }
    )
    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))

    data = response.json()
    return base64.b64decode(data["artifacts"][0]["base64"])

def getImageFromImage(prompt, init_image):
    response = requests.post(
        f"{stability_api_host}/v1/generation/{stability_engine_id}/image-to-image",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {stability_api_key}"
        },
        files={
            "init_image": init_image
        },
        data={
            "text_prompts[0][text]": prompt,
            "text_prompts[0][weight]": 1,
            "image_strength": 0.15,
            "init_image_mode": "IMAGE_STRENGTH",
            "cfg_scale": 7,
            "clip_guidance_preset": "FAST_BLUE",
            "samples": 1,
            "steps": 30,
        }
    )
    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))

    data = response.json()
    return base64.b64decode(data["artifacts"][0]["base64"])


stability_engine_id = "stable-diffusion-xl-beta-v2-2-2"
stability_api_host = os.getenv('API_HOST', 'https://api.stability.ai')
stability_api_key = os.getenv("STABILITY_API_KEY")

#st.session_state
for key, value in st.session_state.items():
    st.session_state[key] = value
# so that clicking "display arther" won't come back to this page
st.session_state["imageSelectedForModification"] = False

if "imageForModification" not in st.session_state:
    st.error("Please select a arther")
    st.stop()
image = st.session_state["imageForModification"]
image_bytes = io.BytesIO(image)
st.image(image)

modOptions = ["", "Modify entire arther", "Modify part of arther"]
mIdx = 0
if "mod_option" in st.session_state:
    mIdx = modOptions.index(st.session_state.mod_option)
modOption = st.selectbox('Would you like to modify your arther by changing a caption or modify part of it?',
                         index=mIdx, options=modOptions, key='mod_option')
if modOption == modOptions[1]:
    renderCaption(image, image_bytes)
if modOption == modOptions[2]:
    renderPartModification(image, image_bytes)
