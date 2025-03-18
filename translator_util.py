from transformers import AutoTokenizer, MarianMTModel

src = "en"  # source language
trg = "hi"  # target language

model_name = f"Helsinki-NLP/opus-mt-{src}-{trg}"
model = MarianMTModel.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

sample_text = "Today's Menu is : Aloo Gobi"
batch = tokenizer([sample_text], return_tensors="pt")

generated_ids = model.generate(**batch)
translated_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
print(translated_text)
