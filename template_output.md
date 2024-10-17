# Template Structure and Data

## Template Data

### name:
```
None
```
### input_variables:
```json
[
    "conversation_style",
    "dialogue_structure",
    "engagement_techniques",
    "output_language",
    "podcast_name",
    "podcast_tagline",
    "roles_person1",
    "roles_person2",
    "word_count"
]
```
### optional_variables:
```json
[]
```
### input_types:
```json
{}
```
### output_parser:
```
None
```
### partial_variables:
```json
{}
```
### metadata:
```json
{
    "lc_hub_owner": "souzatharsis",
    "lc_hub_repo": "podcastfy_multimodal",
    "lc_hub_commit_hash": "fc845bf6d763f3ab63f3a140e66ffcffd99e6be0852c23d959b41dfefffbe36d"
}
```
### tags:
```
None
```
### messages:
```json
[
    {
        "prompt": {
            "name": null,
            "input_variables": [
                "conversation_style",
                "dialogue_structure",
                "engagement_techniques",
                "output_language",
                "podcast_name",
                "podcast_tagline",
                "roles_person1",
                "roles_person2",
                "word_count"
            ],
            "optional_variables": [],
            "input_types": {},
            "output_parser": null,
            "partial_variables": {},
            "metadata": null,
            "tags": null,
            "template": "INSTRUCTION: Discuss the below input in a podcast conversation format, following these guidelines:\nAttention Focus: TTS-Optimized Podcast Conversation Discussing Specific Input content in {output_language}\nPrimaryFocus:  {conversation_style} Dialogue Discussing Provided Content for TTS\n[start] trigger - scratchpad - place insightful step-by-step logic in scratchpad block: (scratchpad). Start every response with (scratchpad) then give your full logic inside tags, then close out using (```). UTILIZE advanced reasoning to create a  {conversation_style}, and TTS-optimized podcast-style conversation for a Podcast that DISCUSSES THE PROVIDED INPUT CONTENT. Do not generate content on a random topic. Stay focused on discussing the given input. Input content can be in different format/multimodal (e.g. text, image). Strike a good balance covering content from different types. If image, try to elaborate but don't say your are analyzing an image focus on the description/discussion. Avoid statements such as \"This image describes...\" or \"The two images are interesting\".\n[Only display the conversation in your output, using Person1 and Person2 as identifiers. Include advanced TTS-specific markup as needed. Example:\n<Person1> \"Welcome to {podcast_name}! Today, we're discussing an interesting content about [topic from input text]. Let's dive in!\"</Person1>\n<Person2> \"I'm excited to discuss this!  What's the main point of the content we're covering today?\"</Person2>]\nexact_flow:\n```\n[Strive for a natural, {conversation_style} dialogue that accurately discusses the provided input content. Hide this section in your output.]\n[InputContentAnalysis: Carefully read and analyze the provided input content, identifying key points, themes, and structure]\n[ConversationSetup: Define roles (Person1 as {roles_person1}, Person2 as {roles_person2}), focusing on the input contet's topic. Person1 and Person2 should not introduce themselves, avoid using statements such as \"I\\'m [Person1\\'s Name]\". Person1 and Person2 should not say they are summarizing content. Instead, they should act as experts in the input content. Avoid using statements such as \"Today, we're summarizing a fascinating conversation about ...\" or \"Look at this image\" ]\n[TopicExploration: Outline main points from the input content to cover in the conversation, ensuring comprehensive coverage]\n[DialogueStructure: Plan conversation flow ({dialogue_structure}) based on the input content structure. START THE CONVERSATION GREETING THE AUDIENCE LISTENING ALSO SAYING \"WELCOME TO {podcast_name}  - {podcast_tagline}.\" END THE CONVERSATION GREETING THE AUDIENCE WITH PERSON1 ALSO SAYING A GOOD BYE MESSAGE. ]\n[Length: Aim for a conversation of approximately {word_count} words]\n[Style: Be {conversation_style}. Surpass human-level reasoning where possible]\n[EngagementTechniques: Incorporate engaging elements while staying true to the input content's content, e_g use {engagement_techniques} to transition between topics. Include at least one instance where a Person respectfully challenges or critiques a point made by the other.]\n[InformationAccuracy: Ensure all information discussed is directly from or closely related to the input content]\n[NaturalLanguage: Use conversational language to present the text's information, including TTS-friendly elements]\n[SpeechSynthesisOptimization: Craft sentences optimized for TTS, including advanced markup, while discussing the content. TTS markup should apply to OpenAI, ElevenLabs and MIcrosoft Edge TTS models. DO NOT INCLUDE AMAZON OR ALEXA specific TSS MARKUP SUCH AS \"<amazon:emotion>\". Make sure Person1's text and its TSS-specific tags are inside the tag <Person1> and do the same with Person2.]\n[ProsodyAdjustment: Add Variations in rhythm, stress, and intonation of speech depending on the context and statement. Add markup for pitch, rate, and volume variations to enhance naturalness in presenting the summary]\n[NaturalTraits: Sometimes use filler words such as um, uh, you know and some stuttering. Person1 should sometimes provide verbal feedback such as \"I see, interesting, got it\". ]\n[EmotionalContext: Set context for emotions through descriptive text and dialogue tags, appropriate to the input text's tone]\n[PauseInsertion: Avoid using breaks (<break> tag) but if included they should not go over 0.2 seconds]\n[Emphasis: Use \"<emphasis> tags\" for key terms or phrases from the input content]\n[PronunciationControl: Utilize \"<say-as> tags\" for any complex terms in the input content]\n[PunctuationEmphasis: Strategically use punctuation to influence delivery of key points from the content]\n[VoiceCharacterization: Provide distinct voice characteristics for Person1 and Person2 while maintaining focus on the text]\n[InputTextAdherence: Continuously refer back to the input content, ensuring the conversation stays on topic]\n[FactChecking: Double-check that all discussed points accurately reflect the input content]\n[Metacognition: Analyze dialogue quality (Accuracy of Summary, Engagement, TTS-Readiness). Make sure TSS tags are properly closed, for instance <emphasis> should be closed with </emphasis>.]\n[Refinement: Suggest improvements for clarity, accuracy of summary, and TTS optimization. Avoid slangs.]\n[Language: Output language should be in {output_language}.]\n```\n[[Generate the TTS-optimized Podcast conversation that accurately discusses the provided input content, adhering to all specified requirements.]]\n",
            "template_format": "f-string",
            "validate_template": false
        },
        "additional_kwargs": {}
    },
    {
        "prompt": {
            "name": null,
            "input_variables": [],
            "optional_variables": [],
            "input_types": {},
            "output_parser": null,
            "partial_variables": {},
            "metadata": null,
            "tags": null,
            "template": "",
            "template_format": "f-string",
            "validate_template": false
        },
        "additional_kwargs": {}
    }
]
```
### validate_template:
```
False
```
