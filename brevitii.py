import discord
import os
import time
import math
from config import MAXIMUM_GEMINI_REQUEST_INPUT_TOKENS, MAXIMUM_MESSAGES_COLLECTION_BATCH_SIZE, MAXIMUM_DISCORD_MESSAGE_LENGTH, model_variant
import google.generativeai as genai

genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

# Dictionary to store the last message timestamp of each user
# TODO: Consider using a database instead of a dictionary.
last_message_timestamps = {}

# Define the cooldown period in seconds
# Brevitii can not serve the same user within the same 12-hour period.
COOLDOWN_PERIOD = 12 * 3600  # 12 hours in seconds

intents = discord.Intents.default()

# This intent is also enabled on the Discord Developer Portal: https://discord.com/developers/applications/
intents.message_content = True

client = discord.Client(intents=intents)


def clean(file_path):
  if (os.path.exists(file_path)):
    os.remove(file_path)


def is_message_allowed(user_id) -> bool:
  # Check if the user's ID is in the last_message_timestamps dictionary
  if user_id in last_message_timestamps:
    # Get the timestamp of the user's last message
    last_message_time = last_message_timestamps[user_id]
    # Get the current time
    current_time = time.time()
    # Check if the time difference is greater than the cooldown period
    if current_time - last_message_time >= COOLDOWN_PERIOD:
      # If the cooldown period has passed, update the timestamp
      last_message_timestamps[user_id] = current_time
      return True

    # If the cooldown period has not passed, the user is not allowed to send a message
    return False

  # If the user's ID is not in the dictionary, they are allowed to send a message
  last_message_timestamps[user_id] = time.time()
  return True


@client.event
async def on_ready():
  print('We have logged in as {}'.format(client.user))


@client.event
async def on_message(message) -> None:
  m_author: discord.User = message.author
  m_guild: discord.Guild = message.guild

  # We only need brevitii to respond to our own messages but not her own.
  # We do this by checking if the Message.author is the same as the Client.user.
  if m_author == client.user:
    return

  if not m_guild:  # Ignore messages in DMs
    return

  # Check https://discordpy.readthedocs.io/en/stable/api.html#discord.TextChannel for more information on TextChannel
  m_channel: discord.TextChannel = message.channel
  m_content: str = message.content

  author_name = m_author.name  # Discord username
  author_global_name = m_author.global_name
  server_name = m_guild.name
  channel_name = m_channel.name

  # Skip messages that are empty
  # This happens if the message is an embed or an attachment
  # TODO: Don't skip messages with attachments
  if m_content == '':
    print('Empty message content')
    return

  if not m_content.startswith('$brief'):
    print('Message is not for Brevitii')
    return

  # Split message content by spaces
  args = m_content.split()

  # Check if the user provided more than one argument
  if len(args) > 2:
    await m_channel.send('Please provide exactly one argument, '
                         'which is the number of messages to abbreviate.\n'
                         'Example: `$brief 5`\n')
    return

  num_messages = -1

  if len(args) > 1:
    # Check https://docs.python.org/3/library/stdtypes.html#str.isdigit for more information on isdigit.
    if not args[1].isdigit():
      await m_channel.send(
          'Please provide a valid number of messages to abbreviate.\n')
      return
    num_messages = int(args[1])

  # Check if the user is allowed to send a message or not.
  # if not is_message_allowed(m_author.id):
  #   await m_channel.send(
  #       'Sorry {}, I can not serve you twice within the same 12-hour period.\n'
  #       .format(author_global_name))
  #   return

  if num_messages == -1:
    # If the user did not provide a number of messages to abbreviate,
    # we will abbreviate as many messages as possible.
    await m_channel.send(
        'Cool {}! I will try to abbreviate as many messages as I can and send you the result in private.'
        .format(author_global_name))
  else:
    await m_channel.send(
        'Cool {}! I will send you the abbreviation of the last {} messages in private.'
        .format(author_global_name, num_messages))

  # Get the directory of the current script
  script_dir = os.path.dirname(os.path.realpath(__file__))
  prompt_body_file_path = os.path.join(script_dir, 'prompt_body.txt')

  # Clean before create.
  clean(prompt_body_file_path)

  ##############################################
  #
  # Here we collect our messages from the chat
  # history.
  #
  ##############################################

  # Currently, we are supporting the text only model
  model = genai.GenerativeModel(model_variant)

  prompt_header_file_path = os.path.join(script_dir, 'prompt_header.txt')

  # Read the header
  with open(prompt_header_file_path, 'r', encoding='utf-8') as file:
    file.seek(0)  # Move the file pointer to the beginning
    prompt_header = file.read()

  # greeting_sentence = 'Hello Gemini!  My name is {}.\n\n'.format(author_name)
  greeting_sentence = ''
  end_sentence = '\n\nConversation ends NOW\n'

  if num_messages == -1:
    await collect_maximum_number_of_messages_and_build_prompt(
        m_channel, prompt_body_file_path, model, prompt_header,
        greeting_sentence, end_sentence)
  else:
    # Collect the last `num_messages` messages
    await collect_messages_and_build_prompt(m_channel, prompt_body_file_path,
                                            num_messages)

  ##############################################
  #
  # Send the abbreviation to the user
  #
  ##############################################

  # Read the body
  with open(prompt_body_file_path, 'a+', encoding='utf-8') as file:
    file.seek(0)  # Move the file pointer to the beginning
    prompt_body = file.read()

  prompt = greeting_sentence + '{}\n\n'.format(
      prompt_header) + prompt_body + end_sentence

  #########################################################################
  # Here we need to check on our body, if it matches (with header and footer) Gemini's maximum length.
  # The header and footer are the same for all messages so we need to truncate only the body.
  # Check https://ai.google.dev/gemini-api/docs/models/gemini#model-variations for more information.
  # Note: For Gemini models, a token is equivalent to about 4 characters. 100 tokens are about 60-80 English words.
  # Truncate the prompt based on the maximum token limit.

  while True:
    num_tokens = model.count_tokens(prompt).total_tokens
    # print(f'Prompt has {num_tokens} tokens.')

    if (num_tokens <= MAXIMUM_GEMINI_REQUEST_INPUT_TOKENS):
      break

    # Calculate the percentage of excess tokens
    excess_percentage = (num_tokens -
                         MAXIMUM_GEMINI_REQUEST_INPUT_TOKENS) / num_tokens

    # Calculate the number of characters to remove based on the percentage
    # Here we round because we need
    chars_to_remove = math.ceil((len(prompt_body) * excess_percentage))

    # Truncate the prompt by removing the calculated number of characters from the end
    # We opt to truncate from the beginning of the body since less crucial messages typically reside there.
    prompt_body = prompt_body[chars_to_remove:]

    prompt = greeting_sentence + '{}\n\n'.format(
        prompt_header) + prompt_body + end_sentence

  #########################################################################

  temp_prompt_file_path = os.path.join(script_dir, 'prompt.txt')

  # Clean before create.
  clean(temp_prompt_file_path)

  # Save the full prompt to a file
  with open(temp_prompt_file_path, 'w', encoding='utf-8') as file:
    file.write(prompt)

  try:
    response = model.generate_content(prompt)
  except Exception as e:
    print("An unexpected error occurred with Gemini: ", e)
    await m_author.send(
        "Hmmmm, it seems like Gemini is down. Please talk to k0T0z about this. Thanks!"
    )
    return

  try:
    if num_messages == -1:
      brevitii_response = 'Here is the abbreviation of messages in the "{}" channel of the "{}" server:\n\n' \
      '{}'.format(channel_name, server_name, response.text)
    else:
      brevitii_response = 'Here is the abbreviation of the last {} messages in the "{}" channel of the "{}" server:\n\n' \
      '{}'.format(num_messages, channel_name, server_name, response.text)
  except Exception as e:
    print("Error accessing response text:", e)
    return

  # Without Discord nitro, the maximum message length is 2000 characters. We need to split the message into multiple messages.
  # With Discord nitro, the maximum message length is 4000 characters.
  if len(brevitii_response) > MAXIMUM_DISCORD_MESSAGE_LENGTH:
    # Split the message into multiple messages
    # https://stackoverflow.com/questions/9475241/split-python-string-every-nth-character
    for i in range(0, len(brevitii_response), MAXIMUM_DISCORD_MESSAGE_LENGTH):
      await m_author.send(brevitii_response[i:i +
                                            MAXIMUM_DISCORD_MESSAGE_LENGTH])
  else:
    await m_author.send(brevitii_response)


async def get_num_brevitii_messages(m_channel_history) -> int:
  num_brevitii_messages = 0

  async for msg in m_channel_history:
    m_content = msg.content

    # Count messages sent from and to Brevitii.
    if msg.author != client.user and not m_content.startswith('$brief'):
      continue

    num_brevitii_messages += 1

  return num_brevitii_messages


async def collect_maximum_number_of_messages_and_build_prompt(
    m_channel: discord.TextChannel, prompt_body_file_path, model,
    prompt_header, greeting_sentence, end_sentence) -> None:

  m_channel_history = m_channel.history()

  accumulative_prompt_body = ""
  messsages_count = 0
  async for msg in m_channel_history:
    m_content = msg.content

    # Skip messages sent from and to Brevitii.
    if msg.author == client.user or m_content.startswith('$brief'):
      continue

    # Skip messages that are empty
    # This happens if the message is an embed or an attachment
    # TODO: Don't skip messages with attachments
    if msg.content == '':
      continue

    collected_msg_author = msg.author

    if msg.reference and msg.reference.resolved:
      referenced_msg = msg.reference.resolved
      referenced_msg_author = referenced_msg.author
      accumulative_prompt_body += '{} (responds to {}): {}\n'.format(
          collected_msg_author.name, referenced_msg_author.name, msg.content)
    else:
      accumulative_prompt_body += '{}: {}\n'.format(collected_msg_author.name,
                                                    msg.content)

    temp_prompt = greeting_sentence + '{}\n\n'.format(
        prompt_header) + accumulative_prompt_body + end_sentence

    num_tokens = model.count_tokens(temp_prompt).total_tokens
    # print(f'Prompt has {num_tokens} tokens.')

    if (num_tokens > MAXIMUM_GEMINI_REQUEST_INPUT_TOKENS):
      break

    # Write to file every MAXIMUM_MESSAGES_COLLECTION_BATCH_SIZE messages collected
    if messsages_count == MAXIMUM_MESSAGES_COLLECTION_BATCH_SIZE:
      with open(prompt_body_file_path, 'a', encoding='utf-8') as file:
        file.write(accumulative_prompt_body)
      accumulative_prompt_body = ""
      messsages_count = 0

    messsages_count += 1

  # Write any remaining messages to file
  if messsages_count > 0:
    with open(prompt_body_file_path, 'a', encoding='utf-8') as file:
      file.write(accumulative_prompt_body)
    accumulative_prompt_body = ""
    messsages_count = 0


async def collect_messages_and_build_prompt(m_channel: discord.TextChannel,
                                            prompt_body_file_path,
                                            num_messages: int = -1) -> None:
  if num_messages == -1:
    print("Invalid number of messages.")
    return

  m_channel_history = m_channel.history(limit=num_messages)

  # Here we remove Brevitii's messages from the number of messages required for
  # abbreviation. We add this value of the num_messages to make sure that we
  # abbreviate the num_messages purely.
  num_brevitii_messages = await get_num_brevitii_messages(m_channel_history)

  del m_channel_history

  m_channel_history = m_channel.history(limit=num_messages +
                                        num_brevitii_messages)

  def write_prompt_to_file(collected_msgs: list,
                           prompt_body_file_path) -> None:
    prompt_body = ""
    for collected_msg in collected_msgs:
      collected_msg_author = collected_msg.author

      if collected_msg.reference and collected_msg.reference.resolved:
        referenced_msg = collected_msg.reference.resolved
        referenced_msg_author = referenced_msg.author
        prompt_body += '{} (responds to {}): {}\n'.format(
            collected_msg_author.name, referenced_msg_author.name,
            collected_msg.content)
        continue

      prompt_body += '{}: {}\n'.format(collected_msg_author.name,
                                       collected_msg.content)

    # Write accumulated messages to the file
    with open(prompt_body_file_path, 'a', encoding='utf-8') as file:
      file.write(prompt_body)

  collected_msgs = []
  async for msg in m_channel_history:
    m_content = msg.content

    # Skip messages sent from and to Brevitii.
    if msg.author == client.user or m_content.startswith('$brief'):
      continue

    # Skip messages that are empty
    # This happens if the message is an embed or an attachment
    # TODO: Don't skip messages with attachments
    if msg.content == '':
      continue

    collected_msgs.append(msg)

    # Write to file every MAXIMUM_MESSAGES_COLLECTION_BATCH_SIZE messages collected
    if len(collected_msgs) == MAXIMUM_MESSAGES_COLLECTION_BATCH_SIZE:
      write_prompt_to_file(collected_msgs, prompt_body_file_path)
      collected_msgs.clear()

  # Write any remaining messages to file
  if len(collected_msgs) > 0:
    write_prompt_to_file(collected_msgs, prompt_body_file_path)
    collected_msgs.clear()
    del collected_msgs


from brevitii_pinger import listen_for_brevitii

listen_for_brevitii()

# Run Brevitii client.
client.run(os.environ['DISCORD_TOKEN'])
