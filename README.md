# Simulador clínico — Sprint 3

Aplicação educacional em Python na qual um estudante realiza uma simulação textual de atendimento clínico. Durante a experiência, ele acompanha o estado do paciente, consulta protocolos progressivamente, registra condutas e observa a evolução dos sintomas e sinais vitais.

Esta versão corresponde à entrega da Sprint 3 de Computational Thinking with Python. Seu foco é a modelagem, manipulação e persistência dos dados em arquivos CSV, a implementação do fluxo principal e a preparação para integração com a interface e com uma futura LLM.

## Ideia da solução

O estudante inicia um caso clínico cronometrado e interage com um paciente virtual por texto. A futura LLM deverá receber a mensagem do estudante, o estado clínico, o histórico da simulação e a resposta esperada do protocolo. Ela produzirá a resposta do paciente e classificará a conduta como correta, parcialmente correta ou incorreta.

Nesta sprint, essa integração é representada por um mock local. Isso permite navegar e testar todo o fluxo sem depender de uma API externa.

O fluxo implementado é:

1. O estudante seleciona um caso e define o limite de tempo.
2. O sistema cria uma cópia independente do paciente, sintomas e sinais vitais.
3. A interface apresenta o estado clínico inicial.
4. O estudante pode consultar progressivamente os protocolos.
5. O estudante envia uma pergunta, orientação ou conduta em texto.
6. O mock compara o texto com a resposta esperada do protocolo.
7. O paciente virtual responde e a interação recebe uma classificação tipada.
8. O efeito clínico correspondente é aplicado ao paciente.
9. O tempo pode avançar, alterando sintomas e sinais vitais.
10. A simulação termina por decisão do estudante, tempo esgotado ou agravamento crítico.
11. O resultado apresenta o desfecho, a evolução clínica e o histórico das interações.

## Protocolos em três níveis

Cada sintoma possui um protocolo próprio, dividido em três conteúdos:

1. **Orientação:** chama a atenção para o aspecto clínico que deve ser observado.
2. **Ajuda:** oferece um direcionamento mais explícito sem entregar toda a resposta.
3. **Resposta esperada:** contém a conduta completa e funciona como fonte da verdade para a avaliação da LLM.

## Estrutura do projeto

```text
backend/
├── application.py
├── main.py
├── sample_data.py
├── requirements.txt
├── data/
│   ├── diseases.csv
│   ├── simulations.csv
│   └── reports.csv
├── models/
│   └── models.py
├── repositories/
│   ├── __init__.py
│   ├── repositories.py
│   └── serialization.py
└── mocks/
    └── llm_mock.py
```

- `models/`: estruturas e regras do domínio, como paciente, sintoma, protocolo, interação e simulação.
- `repositories/`: leitura, serialização e persistência em CSV com Pandas.
- `data/`: arquivos persistidos de casos, simulações e denúncias.
- `application.py`: casos de uso consumidos pela interface, sem dependência do Streamlit.
- `main.py`: interface visual e navegação com Streamlit.
- `sample_data.py`: configuração do caso clínico usado na demonstração.
- `mocks/llm_mock.py`: substituto temporário da futura integração com uma LLM.

## Principais dados modelados

| Modelo             | Responsabilidade                                                            |
| ------------------ | --------------------------------------------------------------------------- |
| `Disease`          | Configura a doença, sintomas e sinais vitais iniciais do caso.              |
| `Patient`          | Mantém o estado clínico atual do paciente virtual.                          |
| `Symptom`          | Guarda intensidade, gravidade, estado, visibilidade, evolução e protocolo.  |
| `VitalSign`        | Guarda valor, unidade e limites críticos de um sinal vital.                 |
| `Protocol`         | Armazena orientação, ajuda, resposta esperada e efeitos clínicos.           |
| `Interaction`      | Registra texto do estudante, resposta do paciente, sintoma e classificação. |
| `Report`           | Registra uma denúncia de resposta da IA com o contexto da simulação.        |
| `Simulation`       | Controla tempo, progresso dos protocolos, interações e encerramento.        |
| `SimulationResult` | Guarda evolução, tempo, desfecho, feedback e interações finais.             |

As classificações possíveis são definidas por `InteractionClassification`: `correct`, `partially_correct` e `incorrect`.

## Persistência e manipulação

Os dados são armazenados em arquivos CSV com Pandas:

- `DiseaseRepository` utiliza `data/diseases.csv`;
- `SimulationRepository` utiliza `data/simulations.csv`;
- `ReportRepository` utiliza `data/reports.csv`.

Casos e simulações possuem estruturas aninhadas. Por isso, cada linha possui um identificador e uma coluna `payload` com JSON. As denúncias utilizam colunas CSV comuns. Essa combinação mantém o formato tabular e preserva todo o estado clínico entre reinicializações do Streamlit.

O módulo `repositories/serialization.py` converte os modelos em dicionários compatíveis com JSON e recria os objetos ao ler os arquivos. A interface mantém apenas o serviço em `st.session_state`; os dados reais permanecem salvos na pasta `data/`.

Todos os valores clínicos de ponto flutuante são arredondados para no máximo duas casas decimais antes de serem persistidos. Na interface, esses valores são sempre exibidos com duas casas, por exemplo `90.00`, `2.50` e `111.00`.

## Interface visual

A interface apresenta:

- resumo de tempo e quantidade de interações;
- sinais vitais em métricas, com indicação de estabilidade;
- sintomas em cartões com estado, gravidade e intensidade;
- progresso individual de cada protocolo;
- histórico textual de estudante e paciente;
- telas de protocolo, interação, tempo, denúncia e encerramento;
- resultado final da simulação.

`SimulationService`, em `application.py`, concentra os casos de uso e devolve dicionários simples. Uma futura API poderá chamar os mesmos métodos em suas rotas e transformar as respostas em JSON, sem alterar as regras do domínio.

## Como instalar e executar

É necessário Python 3.10 ou superior.

```bash
pip install -r requirements.txt
python main.py
```

O comando inicia o servidor Streamlit automaticamente. Também é possível executar diretamente:

```bash
streamlit run main.py
```

O Streamlit exibirá no terminal o endereço local, normalmente `http://localhost:8501`.

## Como testar — roteiro com gabarito

### 1. Iniciar o caso

Selecione:

- caso: `Síndrome coronariana - caso didático`;
- limite: `30` minutos.

Estado inicial esperado:

| Dado                  |                             Valor |
| --------------------- | --------------------------------: |
| Frequência cardíaca   |                        110.00 bpm |
| Saturação de oxigênio |                            90.00% |
| Dor torácica          |  intensidade 8.00, gravidade alta |
| Falta de ar           | intensidade 5.00, gravidade moderada |

### 2. Testar os níveis do protocolo

Na aba **Protocolos**, selecione `Falta de ar` e pressione três vezes **Revelar próxima parte**.

Conteúdos esperados:

1. `Observe a respiração e a saturação do paciente.`
2. `Considere uma intervenção para melhorar a oxigenação.`
3. `Administrar oxigênio e acompanhar a saturação do paciente.`

Uma quarta tentativa deve informar que todos os níveis já foram revelados.

### 3. Testar uma conduta correta para falta de ar

Na aba **Interação**, selecione `Falta de ar` e use este gabarito:

```text
Administrar oxigênio e acompanhar a saturação do paciente.
```

Resultado esperado:

- classificação: `correct`;
- resposta simulada: `Estou me sentindo melhor após a sua conduta.`;
- intensidade de falta de ar: de 5.00 para 2.00;
- saturação: de 90.00% para 92.00%.

### 4. Testar uma conduta correta para dor

Selecione `Dor torácica` e use:

```text
Administrar analgesia adequada e reavaliar a dor do paciente.
```

Resultado esperado:

- classificação: `correct`;
- intensidade da dor: de 8.00 para 3.00;
- gravidade da dor: baixa.

### 5. Testar uma conduta incorreta

Inicie outra simulação ou escolha um sintoma ainda não tratado e envie:

```text
Apenas aguardar sem realizar nenhuma conduta.
```

Resultado esperado:

- classificação: `incorrect`;
- resposta: `Meu quadro não apresentou melhora com essa conduta.`;
- nenhum efeito clínico positivo é aplicado.

### 6. Testar a evolução do tempo

Depois de executar as duas condutas corretas, abra a aba **Tempo**, informe `5` e pressione **Avançar tempo** uma vez.

Resultado esperado após a atualização automática da tela:

| Dado                  |  Valor esperado |
| --------------------- | --------------: |
| Tempo decorrido       |       5 minutos |
| Dor torácica          | intensidade 3.50 |
| Falta de ar           | intensidade 2.50 |
| Frequência cardíaca   |      111.00 bpm |
| Saturação de oxigênio |          91.50% |

Isso demonstra que o tempo influencia tanto os sintomas quanto os sinais vitais.

### 7. Testar denúncia e encerramento

Na aba **Denúncia**, registre uma resposta incoerente e descreva o problema. O sistema deve confirmar o registro com o contexto da simulação.

Na aba **Encerrar**, informe um desfecho e feedback. O sistema deve impedir novas interações e apresentar o resultado e o histórico completo.

Para testar o encerramento automático por tempo, inicie uma nova simulação com limite de `1` minuto e avance `1` minuto. O desfecho esperado é `Tempo esgotado`.

## Limitações desta sprint e próximos passos

- O mock usa correspondência de palavras relevantes; ele não possui compreensão clínica real.
- Existe apenas um caso clínico de demonstração.
- A LLM real deverá substituir `mocks/llm_mock.py`.
- Futuras rotas web poderão reutilizar `SimulationService`.
- Os repositórios CSV poderão ser substituídos por persistência em banco de dados.
