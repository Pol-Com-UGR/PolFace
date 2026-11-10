# Usage notice

*Versión en español: [AVISO_DE_USO.md](AVISO_DE_USO.md).*

`polface` is a **research tool**. It identifies people in video using face recognition, which means processing biometric data. Read this before using it.

## Intended use
- Descriptive analysis of the visibility of **public figures** (for example, politicians) in publicly broadcast audiovisual content such as TV news.
- Academic research, with the authorisations your institution requires.

## Unintended and discouraged uses
- Surveillance, tracking or profiling of private individuals.
- Identifying people who have not given their consent and are not public figures in the context analysed.
- Commercial use (see the model licences below).
- Making decisions about people from the results without human verification.

## Your responsibility as a user
- **You are responsible for legal compliance** in your context: GDPR (face recognition to identify people is processing of biometric data, Art. 9), the EU AI Act, and your institution's rules. Consult your data protection officer and, where relevant, your ethics committee before you start.
- **Do not upload or share the reference gallery** (`galeria.npz`): it contains facial embeddings. The repository already excludes it by default through `.gitignore`; do not change that.
- **Do not publish videos or frames** belonging to third parties unless you hold the rights. Full transcripts of television broadcasts should not be published without checking the rights either; the repository excludes them by default.
- The **results** (`detecciones.csv`) contain people's names per moment of video. Publish only aggregates (such as those from `polface resumen`) unless you have a legal basis for more.
- Reference photos must show public figures and come from sources whose licence allows this use.

## Limitations
- Face recognition **makes mistakes**, and they are not evenly distributed (lighting, angle, age, image quality, the person's features). Screen-time figures are **estimates** based on one frame every N seconds.
- The default threshold (`--umbral 0.5`) is only a starting point. **Validate it against a hand-labelled sample** of your own videos and publish precision and coverage alongside your results.
- **Transcripts do not attribute speech to anyone.** The text attached to each appearance is the audio heard around the moment the person is on screen; speakers are not separated. Do not quote that text as said by them.
- **Sentiment and toxicity.** These are automatic classifiers trained on other kinds of text (reviews, tweets, online comments). They do not measure the political tone of a news item and they flag as toxic any text containing insults or swear words, even when quoted or reported, which can bias results. Only the languages each model declares to support are scored (see the README); validate them against a hand-coded sample in each language.
- Whisper also makes mistakes (proper names, acronyms, noise, music, overlapping speech) and can invent text in passages without speech. Check a sample by hand.
- This version does not infer emotions. If it is added in future it will be an optional module with validity warnings: an algorithm classifying an expression does not show that the person feels that emotion.

## Model licences
The code in this repository is MIT. The pretrained **InsightFace** models (for example `buffalo_l`) are downloaded separately and, according to the project's documentation, may only be used for **non-commercial research**. Check the current terms at <https://github.com/deepinsight/insightface> before using them. The Whisper models (OpenAI) and faster-whisper (SYSTRAN) are distributed under the MIT licence.
