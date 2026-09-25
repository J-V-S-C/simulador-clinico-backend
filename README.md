# Simulador clínico — Sprint 3

## Sobre o projeto

Aplicação educacional em Python para simulações textuais e cronometradas de atendimento clínico.

O estudante interage com um paciente virtual, consulta protocolos e envia condutas. O sistema avalia as interações e atualiza os sintomas e sinais vitais conforme as decisões tomadas e o tempo decorrido.

## Fluxo da simulação

1. selecionar um caso clínico e definir o limite de tempo;
2. visualizar o paciente, seus sintomas e sinais vitais;
3. consultar protocolos em níveis progressivos;
4. enviar uma conduta em texto;
5. receber a resposta do paciente e a avaliação da conduta;
6. avançar o tempo e acompanhar a evolução clínica;
7. encerrar a simulação ou aguardar um encerramento automático;
8. visualizar o resultado e o histórico.

A simulação também termina quando o tempo se esgota ou um sinal vital atinge um valor crítico.

## Protocolos

Cada sintoma possui um protocolo apresentado em três níveis:

1. **Orientação:** indica o que deve ser observado;
2. **Ajuda:** direciona o estudante sem entregar a resposta;
3. **Resposta esperada:** contém a conduta correta e serve como referência para avaliar a interação.

Nesta sprint, um mock baseado em palavras-chave representa a futura LLM e classifica a conduta como `correct`, `partially_correct` ou `incorrect`.

## Estrutura do projeto

```text
backend/
├── application.py           # Fluxo principal da aplicação
├── main.py                  # Interface Streamlit
├── sample_data.py           # Caso clínico de demonstração
├── requirements.txt
├── data/
│   ├── diseases.csv         # Casos clínicos
│   ├── simulations.csv      # Simulações geradas
│   └── reports.csv          # Denúncias geradas
├── models/
│   └── models.py            # Modelos e regras do simulador
├── repositories/
│   ├── repositories.py      # Leitura e gravação dos CSVs
│   └── serialization.py     # Conversão entre objetos e dados persistíveis
└── mocks/
    └── llm_mock.py          # Simulação temporária da LLM
```

O código está separado em quatro partes:

- `models`: representa doença, paciente, sintomas, sinais vitais, protocolos, interações e simulações;
- `repositories`: lê e salva os dados;
- `application.py`: executa os casos de uso sem depender da interface;
- `main.py`: apresenta o fluxo navegável no Streamlit.

Essa separação permite que uma futura API reutilize a camada de aplicação sem alterar as regras do simulador.

## Persistência dos dados

A persistência utiliza Pandas e arquivos CSV:

| Arquivo           | Conteúdo                                   |
| ----------------- | ------------------------------------------ |
| `diseases.csv`    | Casos clínicos configurados                |
| `simulations.csv` | Estado completo e histórico das simulações |
| `reports.csv`     | Denúncias de respostas da IA               |

Casos e simulações possuem uma coluna `payload` em JSON para preservar dados aninhados. Os arquivos são recriados automaticamente quando necessário, e uma simulação pode ser recuperada após reiniciar a aplicação.

Valores clínicos de ponto flutuante são persistidos e exibidos com até duas casas decimais.

## Interface

A interface Streamlit permite:

- iniciar e encerrar uma simulação;
- visualizar sintomas e sinais vitais;
- consultar os três níveis dos protocolos;
- enviar condutas ao paciente virtual;
- avançar o tempo;
- consultar o histórico;
- denunciar uma resposta da IA;
- visualizar o resultado final.

## Tecnologias

- Python 3.10 ou superior;
- Streamlit;
- Pandas.

## Como executar

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute a aplicação:

```bash
python main.py
```

Também é possível usar:

```bash
streamlit run main.py
```

A interface estará disponível normalmente em `http://localhost:8501`.

## Como testar

1. Inicie o caso `Síndrome coronariana - caso didático` com limite de 30 minutos.
2. Confira o estado inicial: frequência cardíaca `110.00 bpm`, saturação `90.00%`, dor torácica `8.00` e falta de ar `5.00`.
3. Em **Protocolos**, revele os três níveis de `Falta de ar`.
4. Em **Interação**, selecione `Falta de ar` e envie:

```text
Administrar oxigênio e acompanhar a saturação do paciente.
```

Resultado esperado: classificação `correct`, falta de ar `2.00` e saturação `92.00%`.

5. Selecione `Dor torácica` e envie:

```text
Administrar analgesia adequada e reavaliar a dor do paciente.
```

Resultado esperado: classificação `correct` e dor `3.00`.

6. Avance cinco minutos uma única vez.

Resultado esperado: tempo `5`, dor `3.50`, falta de ar `2.50`, frequência cardíaca `111.00 bpm` e saturação `91.50%`.

7. Registre uma denúncia e encerre o atendimento. O resultado deve apresentar o desfecho e o histórico das interações.
8. Para testar o tempo esgotado, inicie outra simulação com limite de um minuto e avance um minuto.

## Limitações

- apenas um caso clínico de demonstração;
- mock simples no lugar de uma LLM real;
- persistência local em CSV;
- sem autenticação ou API web nesta sprint.
