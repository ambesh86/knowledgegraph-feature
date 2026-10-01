import logging
from pathlib import Path

from model2vec import StaticModel
from sentence_transformers import SentenceTransformer
from sentence_transformers.models import StaticEmbedding

logger = logging.getLogger(__name__)


class EmbeddingProvider:

    def __init__(self, model_cache_dir: str | None):
        self.local_path = model_cache_dir

    def init_model(self) -> SentenceTransformer | StaticModel:
        return self._model_from_pretrained()

    def _model_from_distillation(self, pca_dims: int = 256) -> SentenceTransformer:
        # todo: get this to work,
        # I see
        # INFO:model2vec.distill.distillation:Explained variance: 0.016.
        # Then an error to download the model
        # https://huggingface.co/blog/Pringled/model2vec
        # model = "BAAI/bge-base-en-v1.5"
        model = "tmp/models/all-mp-net-base-v2"
        device = "cuda"  # "cpu" "mps" Or None to autoselect
        logger.info(f"using model {model}")
        static_embedding = StaticEmbedding.from_distillation(
            model, device=device, pca_dims=pca_dims
        )
        model = SentenceTransformer(modules=[static_embedding])
        return model

    def _model_from_pretrained(self) -> StaticModel:
        model_name = "minishlab/potion-base-8M"
        logger.info(f"using model {model_name}")
        if self.local_path is not None:
            model_path = Path(self.local_path) / model_name
        else:
            model_path = Path(model_name)
        logger.info(f"model path {model_path}")
        model = StaticModel.from_pretrained(path=model_path, token=None)
        return model

    def _model_from_sentence_transformer(self) -> SentenceTransformer:
        # all-MiniLM-L6-v2 will let us also do embeddings in the browser
        # https://huggingface.co/Xenova/all-MiniLM-L6-v2
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        # model_name = "intfloat/e5-mistral-7b-instruct"
        # model_name = "models--sentence-transformers--all-mpnet-base-v2"
        model = f"{self.local_path}/{model_name}"
        device = "mps"  # cpu, mps, cuda Or None to autoselect
        logger.info(f"using model {model}")
        model = SentenceTransformer(model_name_or_path=model_name, device=device)
        return model
