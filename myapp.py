import streamlit as st
import base64
import os
import io
import requests
import openai
import threading
import numpy as np
import re
import random
from streamlit_cropper import st_cropper
from PIL import Image
import replicate


class openAiChatThread(threading.Thread):
    def __init__(self, name, prompt):
        threading.Thread.__init__(self)
        self.prompt = prompt
        self.name = name
        self.res = ""

    def run(self):
        chatCompletionResponse = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": self.prompt}]
        )
        self.resp = chatCompletionResponse.choices[0].message.content


def parseNumberedList(s):
    numberedItems = s.split('\n')
    items = []
    for item in numberedItems:
        x = re.findall("[a-zA-Z]+", item)
        items.append(x[0])
    return items


@st.cache_data(show_spinner='')
def getGPTThemes(text):
    userPromptThread = openAiChatThread("user",
                                        f"Give a list of emotions expressed by this statement: {text}")
    artherPromptThread = openAiChatThread("arther",
                                          f"Give a list of positive one-word art therapy prompts for {text}")

    userPromptThread.start()
    artherPromptThread.start()

    userPromptThread.join()
    artherPromptThread.join()

    userThemes = parseNumberedList(userPromptThread.resp)
    artherThemes = parseNumberedList(artherPromptThread.resp)

    if len(userThemes) > K:
        userThemes = random.sample(userThemes, K)
    if len(artherThemes) > K:
        artherThemes = random.sample(artherThemes, K)
    return userThemes + artherThemes

    #return ["Sadness", "Frustration", "Helplessness", "Strength", "Inner", "Growth"]


@st.cache_data(show_spinner="Generating caption...")
def getCaption(image_bytes):
    return replicate.run(
        "methexis-inc/img2prompt:50adaf2d3ad20a6f911a8a9e3ccf777b263b8596fbd2c8fc26e8888f8a0edbb5", input={"image": image_bytes})


@st.cache_data(show_spinner="Generating your arthers...")
def getImagesFromText(journal_entry: str):
    response = requests.post(
        f"{api_host}/v1/generation/{engine_id}/text-to-image",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {stability_api_key}"
        },
        json={
            "text_prompts": [
                {
                    "text": f"spiritual painting based on:\n {journal_entry}",
                    "weight": 1
                },
                {
                    "text": f"person making a drawing",
                    "weight": -10
                },
                {
                    "text": f"pencil",
                    "weight": -20
                }
            ],
            "cfg_scale": 7,
            "clip_guidance_preset": "FAST_BLUE",
            "height": 512,
            "width": 512,
            "samples": num_samples,
            "steps": 30,
        },
    )
    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))

    data = response.json()
    images = []
    for im in data["artifacts"]:
        images.append(base64.b64decode(im["base64"]))
    return images


def getImageFromImage(prompt, init_image):
    response = requests.post(
        f"{api_host}/v1/generation/{engine_id}/image-to-image",
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


def getInpaintedImage(prompt, init_image, mask):
    response = requests.post(
        f"{api_host}/v1/generation/{engine_id}/image-to-image/masking",
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


def checkboxCallback(key, idx):
    for i in range(num_samples):
        artherKey = "arther_" + str(i)
        if artherKey != key:
            st.session_state[artherKey] = False
    st.session_state["imageIdxForModification"] = idx


def renderArthers(prompt):
    cols = st.columns(num_samples, gap="small")
    images = getImagesFromText(prompt)
    for i, im in enumerate(images):
        cols[i].image(im)

    st.write("\n\n\n Would you like to modify an arther? If so, please select it")
    for i, c in enumerate(cols):
        with c:
            key = "arther_" + str(i)
            st.checkbox(key, value=False, key=key, label_visibility="hidden",
                        on_change=checkboxCallback, args=(key, i))

    if "imageIdxForModification" in st.session_state and st.session_state["imageIdxForModification"] >= 0:
        image = images[st.session_state["imageIdxForModification"]]
        image_bytes = io.BytesIO(image)
        modOptions = ["", "Modify entire arther", "Modify part of arther"]
        modOption = st.selectbox(
            'Would you like to modify your arther by changing a caption or modify part of it?', modOptions)
        if modOption == modOptions[1]:
            renderCaption(image, image_bytes)
        if modOption == modOptions[2]:
            renderPartModification(image, image_bytes)


def renderCaption(image, image_bytes):
    caption = getCaption(image_bytes)
    mod_caption = st.text_area(
        'Below is a descriptive caption for your arther. You can modify it.', caption)
    if mod_caption and mod_caption != caption:
        with st.spinner('Generating your modified arther'):
            st.image(getImageFromImage(mod_caption, image))


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


num_samples = 3
K = 3
images = []
st.title("Arther")
journal = st.text_input('How are you feeling today?', '')
engine_id = "stable-diffusion-xl-beta-v2-2-2"
api_host = os.getenv('API_HOST', 'https://api.stability.ai')
stability_api_key = os.getenv("STABILITY_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

if stability_api_key is None:
    raise Exception("Missing Stability API key.")
if openai.api_key is None:
    raise Exception("Missing OpenAI API key.")

if len(journal) > 0:
    themes = getGPTThemes(journal)
    theme = st.selectbox(
        'Would you like your ather to be directly based on your journal entry or one of these themes?',
        ["", "Directly based on journal"] + themes, key="themeOption")
    if theme:
        prompt = journal
        if theme in themes:
            prompt = theme
        renderArthers(prompt)
