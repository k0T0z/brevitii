# Brevitii Bot

> [!IMPORTANT]
> Here is the invite link: https://discord.com/oauth2/authorize?client_id=1230505478967005224&permissions=68608&scope=bot

# Usage

You can call Brevitii by ``$brief`` and then tell her how many messages you want to abbreviate. For example:

```
$brief 10000
```

# Compiling

Create a .env file that contains the following:

```
DISCORD_TOKEN=
GOOGLE_API_KEY=
```

then download the dependencies:

```bash
pip install -r requirements.txt
```

then run using:

```bash
python brevitii.py
```

# Improving Gemini's prompt for Brevitii

See [Prompting Intro](https://ai.google.dev/gemini-api/docs/prompting-intro) by Google.

# TODO

- Brevitii will be very helpful if we can ask here about specific things in the abbreviation. For example, if we want the links Brevitii mentioned.
- While deploying Brevitii for continuous operation is our top priority, our current student status means we're unable to invest in a cloud service at this time.
- Enhance the Discord prompt to better suit Gemini's analysis. Remove irrelevant elements like user IDs (mentions) and replace them with ``Global Names`` to ensure greater accuracy in the analysis process.
- Enhance Brevitii by integrating support for the ``gemini-pro-vision`` model, enabling it to process images along with text in the chat. Additionally, empower Brevitii to forward these images to the requester if deemed relevant by the Gemini model.
- Enhance Brevitii by integrating support for the ``gemini-1.5-pro-latest`` model, enabling it to process videos (stream of images + audio) along with text in the chat. Additionally, empower Brevitii to forward these videos to the requester if deemed relevant by the Gemini model.
- Address the issue of prompt truncation. If the token count surpasses the limit, truncate the prompt accordingly to ensure it remains within the specified boundaries.
- Limit the usage for each user by integrating a Database.

# Notes

- Limited number of tokens for ``gemini-pro`` model. It offers a maximum of 30'720 tokens. This means the request prompt length must not exceed 122'880 characters as each token is equivalent to about 4 characters. See [Model Variations](https://ai.google.dev/gemini-api/docs/models/gemini#model-variations) for more information. During our prompt testing, we encountered an edge case where the maximum number of tokens was not 30'720 as expected, but rather 30'712. We've shared this feedback with the Gemini developers for further review.
- Quality of prompt. The quality of LLMs' prompts is always a problem.
- Limited single message length in Discord. In Discord's free tier, messages are limited to 2'000 characters each, while the ``gemini-pro`` model can generate approximately 8'192 characters, equivalent to 2'048 tokens. However, in Discord's Nitro, messages are limited to 4'000 characters each which is still a problem. See [Model Variations](https://ai.google.dev/gemini-api/docs/models/gemini#model-variations) for more information. We solved this by sending the response in batches if the message length exceeded the limit.
