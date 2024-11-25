MAXIMUM_MESSAGES_COLLECTION_BATCH_SIZE = 100
MAXIMUM_DISCORD_MESSAGE_LENGTH = 2000

# Check https://ai.google.dev/gemini-api/docs/models/gemini#model-variations for more information.
# Note: For Gemini models, a token is equivalent to about 4 characters. 100 tokens are about 60-80 English words.
# TODO: What is the best number of tokens?
MAXIMUM_GEMINI_REQUEST_INPUT_TOKENS = 30712

# Check https://ai.google.dev/gemini-api/docs/models/gemini#model-variations
model_variant = 'gemini-1.5-flash-8b'
