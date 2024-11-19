import torch
from transformers import LongformerForSequenceClassification, LongformerTokenizer
import os
import config

# Load the fine-tuned model and tokenizer
model_path = os.path.join(config.DATADIR, 'ml_models', 'mail-longformer-classifier-4096')
model_LF = LongformerForSequenceClassification.from_pretrained(model_path)
tokenizer_LF = LongformerTokenizer.from_pretrained(model_path)

# Set the model to evaluation mode
model_LF.eval()

# Move the model to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_LF.to(device)

def predict_category(text):
    # Tokenize the input text
    inputs = tokenizer_LF(text, return_tensors="pt", truncation=True, padding=True, max_length=4096)
    
    # Move inputs to the appropriate device
    inputs = {key: value.to(device) for key, value in inputs.items()}
    
    # Get model predictions
    with torch.no_grad():
        outputs = model_LF(**inputs)

    # Get the predicted label
    predicted_label = torch.argmax(outputs.logits, dim=1).item()
    return predicted_label

# Example usage
text_input = input("Enter the email message body:\n")
category = predict_category(text_input)
print(f"Predicted Category: {category}")
