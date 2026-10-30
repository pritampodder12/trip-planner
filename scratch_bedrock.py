import os

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse

load_dotenv()
model = ChatBedrockConverse(
    model=os.environ["LLM_MODEL_ID"], region_name=os.environ["AWS_REGION"]
)
print(model.invoke("Say hello in one short sentence.").content)
