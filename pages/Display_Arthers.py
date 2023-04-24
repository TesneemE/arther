import streamlit as st
import base64
import os
import requests
import openai
import threading
import re
import random
from streamlit_extras.switch_page_button import switch_page


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

    # return ["Sadness", "Frustration", "Helplessness", "Strength", "Inner", "Growth"]


@st.cache_data(show_spinner="Generating your arthers...")
def getImagesFromText(style: str, journal_entry: str):
    response = requests.post(
        f"{stability_api_host}/v1/generation/{stability_engine_id}/text-to-image",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {stability_api_key}"
        },
        json={
            "text_prompts": [
                {
                    "text": f"an {style} painting based on:\n {journal_entry}",
                    "weight": 1
                },
                {
                    "text": f"person making a painting",
                    "weight": -10
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


def checkboxCallback(key, image):
    for i in range(num_samples):
        artherKey = "arther_" + str(i)
        if artherKey != key:
            st.session_state[artherKey] = False
    if st.session_state[key]:
        st.session_state["imageForModification"] = image
        st.session_state["imageSelectedForModification"] = True


def renderArthers(style, prompt):
    cols = st.columns(num_samples, gap="small")
    images = getImagesFromText(style, prompt)
    for i, im in enumerate(images):
        cols[i].image(im)

    st.write("\n\n\n Would you like to modify an arther? If so, please select it")
    for i, c in enumerate(cols):
        with c:
            key = "arther_" + str(i)
            st.checkbox(key, value=False, key=key, label_visibility="hidden",
                        on_change=checkboxCallback, args=(key, images[i]))


num_samples = 3
K = 3
images = []
stability_engine_id = "stable-diffusion-xl-beta-v2-2-2"
stability_api_host = os.getenv('API_HOST', 'https://api.stability.ai')
stability_api_key = os.getenv("STABILITY_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")


# This is a weird workaround for the case that on the first run
# of this page this state from Home.py is available but when any
# input causes this page to re-run, any carried-over state is cleared.
# Therefore we are 'transferring' the Home state to this page's state
for key, value in st.session_state.items():
    st.session_state[key] = value
st.session_state["switch_page_from_home"] = False


if "imageSelectedForModification" in st.session_state and st.session_state.imageSelectedForModification:
    switch_page("Modify Arther")
else:
    if ("journal" not in st.session_state) or ("style" not in st.session_state):
        st.error("Please specify a journal entry and style")
        st.stop()
    themes = getGPTThemes(st.session_state.journal)
    st.selectbox(
        'Would you like your ather to be directly based on your journal entry or one of these themes?',
        ["", "Directly based on journal"] + themes, key="theme_option")
    if st.session_state.theme_option:
        prompt = st.session_state.journal
        if st.session_state.theme_option in themes:
            prompt = st.session_state.theme_option
        renderArthers(st.session_state.style, prompt)
