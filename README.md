# Simulador Clínico — backend em Python

Backend do MVP funcional do Challenge FIAP + Hospital Moinhos de Vento. A API recebe ações do estudante, aplica as regras da simulação, consulta o Gemini para gerar e avaliar a resposta do paciente virtual, salva a tentativa e devolve ao frontend o estado atualizado e o resultado. Os casos e pacientes são fictícios; o sistema tem finalidade educacional.

**API publicada pela equipe:** [documentação interativa na VPS Oracle](https://clinical-simulator-api.duckdns.org/docs) · [verificação de saúde](https://clinical-simulator-api.duckdns.org/api/health)

**Código:** [backend](https://github.com/J-V-S-C/simulador-critico-backend) · [frontend](https://github.com/J-V-S-C/Simulador-clinico-front)

**Equipe:** [integrantes](INTEGRANTES.txt)

## Estrutura da solução em Python

| Requisito | Como foi implementado |
| --- | --- |
| Modelagem e manipulação de dados | `models/` define caso, paciente, sintomas, sinais vitais, interações, protocolos e resultado. `repositories/` converte esses objetos em dados persistidos e os lê de volta. |
| Funções e módulos do fluxo principal | `services/` implementa cadastro, escolha de caso, início da tentativa, ações, evolução temporal, encerramento, resultado e relatos de respostas. |
| Integração com a solução visual | O frontend Next.js usa a API FastAPI para enviar ações e exibir o estado salvo. O percurso navegador → API → banco → navegador está registrado na [validação do frontend](https://github.com/J-V-S-C/Simulador-clinico-front/blob/main/docs/VALIDATION.md). |
| Organização, documentação e testes | Os contratos ficam em `routes/schemas.py`, as rotas em `routes/api.py` e os testes em `tests/`. Este README explica instalação, execução e verificação. |

O banco guarda contas e hashes de senha, hashes dos tokens de acesso, modelos de casos, tentativas com o estado clínico e histórico, relatos de respostas e avaliações da experiência. A tentativa pertence a uma conta; as consultas e alterações usam esse vínculo. O SQLite é o armazenamento local padrão, com migrações Alembic. O CSV de casos em `data/diseases.csv` é uma fonte legada importada na inicialização; novas tentativas são gravadas no banco SQL.

Após cada tentativa encerrada, o estudante pode avaliar a experiência. O script `feedback_summary.py` lê esses dados e calcula total de respostas, proporção positiva, médias e distribuição das notas de clareza e dificuldade. Os números dependem das respostas coletadas; o repositório não inclui dados de usuários.

## Tecnologias e organização

- **Python 3.12+ e FastAPI:** API JSON em `/api` e documentação OpenAPI em `/docs`.
- **Pydantic:** contratos explícitos e validação de entrada e saída.
- **SQLAlchemy e Alembic:** persistência e migrações. SQLite é o padrão; PostgreSQL pode ser configurado por `DATABASE_URL`.
- **SDK oficial `google-genai`:** fala do paciente e avaliação da interação, com saída validada antes de alterar o estado clínico.
- **Pytest:** testes de autenticação, casos, simulações, relatórios, feedback e persistência SQL.

| Diretório ou arquivo | Responsabilidade |
| --- | --- |
| `server.py`, `routes/`, `handlers/` | Inicialização, rotas HTTP, autenticação e tradução de erros. |
| `models/` | Estados, regras clínicas e transições da simulação. |
| `services/` | Casos de uso de cadastro, casos, simulações e relatórios. |
| `ports/` | Interfaces para relógio, avaliador e armazenamento. |
| `repositories/`, `migrations/` | Banco SQL, importação dos CSV antigos e evolução do esquema. |
| `integrations/gemini.py` | Comunicação com Gemini e validação da resposta. |
| `feedback_summary.py` | Resumo das avaliações coletadas após as simulações. |

## Executar localmente

Entre na pasta `backend/` e use Python 3.12 ou mais recente:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Defina `GEMINI_API_KEY` em `.env` para usar as interações com IA. `GOOGLE_API_KEY` também é aceito e tem prioridade se ambas estiverem definidas. A chave fica somente no servidor. Sem chave, a API inicia, mas uma interação que precise do Gemini retorna `503`. Para instalar apenas as dependências de execução, use `requirements.txt` no lugar de `requirements-dev.txt`.

```bash
.venv/bin/python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

Acesse `http://127.0.0.1:8000/docs` ou consulte `http://127.0.0.1:8000/api/health`. Para rodar a interface local, siga o [README do frontend](https://github.com/J-V-S-C/Simulador-clinico-front#readme) e configure `API_BASE_URL=http://127.0.0.1:8000/api`.

| Variável | Uso |
| --- | --- |
| `GEMINI_API_KEY` ou `GOOGLE_API_KEY` | Chave privada do Gemini, usada apenas pela API. |
| `GEMINI_MODEL` | Modelo de IA; padrão `gemini-3.5-flash-lite`. |
| `GEMINI_TIMEOUT_SECONDS` | Tempo limite da chamada ao Gemini; padrão de 15 segundos. |
| `DATABASE_URL` | Banco SQL; por padrão, SQLite em `backend/data/clinical.db`. |
| `ALLOWED_ORIGINS` | Origens exatas do frontend aceitas pelo CORS, separadas por vírgula. |

Na inicialização, o servidor aplica as migrações Alembic, importa de forma idempotente CSV legados disponíveis em `data/` e atualiza os modelos de casos. Novas tentativas são salvas no banco SQL; tentativas já iniciadas preservam o caso gravado na criação.

## Fluxo funcional e regras

1. O estudante se cadastra ou faz login e recebe um token Bearer válido por oito horas.
2. O frontend lista os casos e cria uma tentativa com duração de 1 a 10 minutos. O backend guarda o caso, sintomas, sinais vitais e relógio.
3. A cada consulta ou ação, o backend reconcilia o tempo real decorrido. Também é possível avançar o tempo simulado de 1 a 600 segundos por requisição.
4. O estudante escolhe um sintoma visível e envia uma pergunta ou conduta. O Gemini gera a fala do paciente e avalia a resposta; o backend valida essa saída e aplica as regras de evolução. A resposta definitiva só aparece depois de persistida. Há uma rota de eventos para exibir uma prévia durante a geração.
5. O estudante pode revelar níveis do protocolo, registrar um problema em uma resposta da IA e consultar o resultado. A simulação termina quando o tempo acaba, ocorre agravamento crítico, todas as queixas são abordadas ou o estudante a encerra.
6. Após o encerramento, o estudante pode enviar ou editar uma avaliação da experiência. Cada tentativa aceita uma avaliação, acessível somente ao seu dono.

O backend é a fonte de verdade para classificação, tempo, evolução e resultado; o frontend não envia o desfecho clínico. A conclusão bem-sucedida e a estabilização final são simplificações didáticas. Os protocolos são material de ensino adaptado de fontes públicas do [NHS](https://www.nhs.uk/conditions/) e devem passar por revisão clínica antes de uso institucional.

## API

Todas as rotas abaixo começam com `/api`. Cadastro, login e saúde são públicos; as demais exigem `Authorization: Bearer <access_token>`. Para testar em `/docs`, faça login e informe **somente o token** no botão **Authorize**.

| Método | Rota | Finalidade |
| --- | --- | --- |
| GET | `/health` | Verificar a disponibilidade do banco. |
| POST | `/auth/register`, `/auth/login`, `/auth/logout` | Cadastrar, autenticar e revogar o token. |
| GET | `/auth/me` | Consultar a conta autenticada. |
| GET | `/cases`, `/cases/{case_id}` | Listar casos e consultar seus limites. |
| POST, GET | `/simulations` | Iniciar tentativa e listar as próprias tentativas. |
| GET | `/simulations/{id}` | Consultar estado, histórico, protocolos e tempo. |
| POST | `/simulations/{id}/interactions` | Enviar pergunta ou conduta e receber o estado salvo. |
| POST | `/simulations/{id}/interactions/stream` | Receber prévia por eventos e, depois, a interação persistida. |
| POST | `/simulations/{id}/time/advance` | Avançar o tempo simulado. |
| POST | `/simulations/{id}/protocols/{symptom_name}/reveal` | Revelar o próximo nível do protocolo. |
| POST | `/simulations/{id}/reports` | Reportar uma interação armazenada. |
| POST | `/simulations/{id}/finish` | Encerrar a tentativa. |
| GET | `/simulations/{id}/result` | Consultar o resultado final. |
| GET, POST, PUT | `/simulations/{id}/experience-feedback` | Consultar, enviar ou editar a avaliação da experiência. |

Os esquemas completos estão no [OpenAPI publicado](https://clinical-simulator-api.duckdns.org/docs). Erros de validação retornam `422`; erros de domínio e dependências usam `{"error":{"code":"...","message":"..."}}` com status apropriado, como `401`, `404`, `409` e `503`.

## Testes e análise dos dados

```bash
.venv/bin/python -m pytest -q tests
.venv/bin/python feedback_summary.py
```

O primeiro comando executa a suíte sem depender de chave Gemini real; nesta revisão, **67 testes passaram**. O segundo lê o banco definido em `DATABASE_URL` e imprime o resumo das avaliações coletadas. Revise comentários livres antes de divulgá-los e compartilhe dados agregados.

## Publicação na VPS Oracle

A API publicada pela equipe usa o domínio `clinical-simulator-api.duckdns.org`. Na VPS, mantenha `DATABASE_URL` em disco persistente, por exemplo `sqlite:////var/lib/simulador/clinical.db`, e configure a chave Gemini e `ALLOWED_ORIGINS` somente no servidor. Publique FastAPI atrás de HTTPS, com a porta da aplicação restrita ao loopback. O frontend deve apontar `API_BASE_URL` para `https://clinical-simulator-api.duckdns.org/api`.

Faça backups consistentes do SQLite com `.backup`; copiar apenas um `.db` em uso pode perder alterações presentes no WAL. Para o roteiro de infraestrutura, consulte [DEPLOY_ORACLE_VERCEL.md](DEPLOY_ORACLE_VERCEL.md). SQLite atende a uma VPS única com tráfego moderado; concorrência alta ou múltiplas instâncias de API exigem reavaliar o banco e os limites de requisições.

**Segurança da publicação:** senhas são armazenadas como hash, os tokens persistidos também são hashes e o acesso às tentativas exige autenticação e vínculo com o proprietário. Chaves e banco local estão fora do Git pelo `.gitignore`. A API ainda não implementa limite de requisições para cadastro, login e chamadas ao Gemini; configure esse limite no proxy ou na aplicação para reduzir tentativas de força bruta e consumo indevido da cota de IA.
