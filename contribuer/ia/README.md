# 🤖 Contribuer avec l'aide d'une IA

**Tu as trouvé une info intéressante** (le budget de ta commune, une ligne de dépense, un rapport…) **et tu veux l'ajouter au projet — mais tu ne connais rien à git, GitHub, ou l'informatique ?** Cette page est pour toi.

Le principe : **ton assistant IA fait le travail technique, toi tu fournis la source.** N'importe quel modèle fait l'affaire.

## Les 3 étapes

1. **Rassemble ta source officielle** : le lien (data.gouv, un PDF, le site d'une collectivité…), le chiffre, l'année, la date où tu l'as consultée.
2. **Ouvre ton IA, colle le prompt prêt ci-dessous** (choisis ton modèle) et ajoute ton info. L'IA te rend un petit bloc **JSON** et te dit **quel fichier** modifier.
3. **Propose la modif dans le navigateur** : sur GitHub, bouton **✏️ Edit** → colle → **Propose changes**. La *pull request* s'ouvre toute seule. Zéro terminal.

Le détail complet (format, où ranger, étapes navigateur illustrées) est dans **[kit-de-contribution.md](kit-de-contribution.md)**.

## Choisis ton IA

| Modèle | Prompt prêt à coller | Note |
|---|---|---|
| **ChatGPT** (OpenAI) | [prompts/chatgpt.md](prompts/chatgpt.md) | Peut lire les liens que tu donnes |
| **Claude** (Anthropic) | [prompts/claude.md](prompts/claude.md) | Colle le contenu du fichier si l'IA ne peut pas naviguer |
| **Gemini** (Google) | [prompts/gemini.md](prompts/gemini.md) | Peut lire les liens |
| **Perplexity** | [prompts/perplexity.md](prompts/perplexity.md) | Idéal pour retrouver et vérifier la source |
| **Le Chat** (Mistral) | [prompts/le-chat.md](prompts/le-chat.md) | Modèle français |
| **LLM local** (Ollama, LM Studio…) | [prompts/llm-local.md](prompts/llm-local.md) | Prompt auto-suffisant, hors-ligne |

## Tu utilises un assistant de code (Claude Code, Cursor, Gemini CLI…) ?

Chemin « avancé » : ouvre le dépôt avec ton agent, il lit automatiquement le fichier d'instructions correspondant et peut faire toute la contribution (y compris la PR) pour toi :

- **Claude Code** → [`CLAUDE.md`](../../CLAUDE.md) + skill [`.claude/skills/contribuer-donnee`](../../.claude/skills/contribuer-donnee/SKILL.md)
- **Codex / Cursor / agents génériques** → [`AGENTS.md`](../../AGENTS.md)
- **Gemini CLI** → [`GEMINI.md`](../../GEMINI.md)

## Rappels

- **Toujours une source officielle.** Pas de chiffre « de tête ».
- **Neutralité** : on documente, on ne juge pas.
- Pas de donnée fiable ? Crée un nœud `inconnu` avec le bon contact — c'est utile.
