
import torch
import open_clip
from PIL import Image

class LeafFilter:

    def __init__(
        self,
        device="cuda",
        model_name="ViT-B-32",
        pretrained="laion2b_s34b_b79b",
        threshold=0.5,
    ):
        self.device = device
        self.threshold = threshold

        self.model, _, self.preprocess = (
            open_clip.create_model_and_transforms(
                model_name,
                pretrained=pretrained,
            )
        )

        self.model = self.model.to(device).eval()

        self.tokenizer = open_clip.get_tokenizer(model_name)

        self.prompts = [
            "a photo of a green leaf",
            "a photo of a leaf of a houseplant",

            "a photo of a plant stem",
            "a photo of a terracotta flower pot",
            "a photo of a wall",
            "a photo of the floor",
            "a photo of soil",
            "a photo of a shadow",
            "a photo of a tile or pavement",
        ]

        self.num_leaf_prompts = 2

        with torch.no_grad():
            text = self.tokenizer(self.prompts).to(device)
            self.text_features = self.model.encode_text(text)
            self.text_features /= self.text_features.norm(
                dim=-1,
                keepdim=True,
            )

    @torch.no_grad()
    def score(self, image, masks, batch_size=32):

        if not masks:
            return []

        scores = []

        for i in range(0, len(masks), batch_size):

            batch_masks = masks[i:i + batch_size]

            crops = []

            for mask in batch_masks:
                x, y, w, h = map(int, mask["bbox"])

                crop = image[y:y+h, x:x+w]

                seg = mask["segmentation"][y:y+h, x:x+w]

                white = crop.copy()
                white[~seg] = 255

                crops.append(
                    self.preprocess(
                        Image.fromarray(white)
                    )
                )

            images = torch.stack(crops).to(self.device)

            image_features = self.model.encode_image(images)

            image_features /= image_features.norm(
                dim=-1,
                keepdim=True,
            )

            logits = 100 * image_features @ self.text_features.T

            probabilities = logits.softmax(dim=-1)

            leaf_score = probabilities[
                :, :self.num_leaf_prompts
            ].sum(dim=-1)

            scores.extend(
                leaf_score.cpu().tolist()
            )

        return scores

    def filter(self, image, masks):

        scores = self.score(image, masks)

        leaf_masks = []

        for mask, score in zip(masks, scores):

            mask["leaf_prob"] = float(score)

            if score >= self.threshold:
                leaf_masks.append(mask)

        return leaf_masks