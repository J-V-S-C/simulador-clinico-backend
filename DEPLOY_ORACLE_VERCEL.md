# Publicar com Vercel + Oracle Always Free

Esta é a opção inicial para um projeto educacional pequeno: Next.js na Vercel Hobby, FastAPI em uma VM Oracle Ampere A1 Always Free e SQLite no disco local persistente da VM. Não é necessária uma conta Supabase para permitir usuários simultâneos. Confirme no painel dos provedores os limites e a elegibilidade gratuitos antes de criar recursos; a capacidade da VM e as cotas do Gemini não são garantidas.

## 1. Preparar o código

- Publique as alterações dos repositórios de frontend e backend em Git. Eles são repositórios separados neste workspace.
- Rode `.venv/bin/python -m pytest -q tests` no backend e `npm run typecheck && npm run build` no frontend.
- Mantenha `backend/.env`, `.env.local`, chaves Gemini e `clinical.db` fora do Git.

## 2. API e banco na Oracle

1. Crie uma VM **Always Free** na região principal da conta, preferindo **VM.Standard.A1.Flex** (ARM). Se a região não oferecer capacidade, aguarde ou teste outro domínio de disponibilidade. Não selecione recursos fora dos limites Always Free. O plano gratuito atual equivale a até **2 OCPUs e 12 GB de RAM** em A1, e **200 GB** de volumes de bloco no total, contando o disco de inicialização.
2. Instale Python 3.12+, Git, `sqlite3` e um proxy HTTPS, como Caddy. Faça o clone do backend em um diretório estável, por exemplo `/opt/simulador/backend`, e instale `requirements.txt` em `.venv`.
3. Crie um diretório persistente e gravável pelo usuário que executará a API: `/var/lib/simulador`. No `backend/.env`, configure:

   ```dotenv
   DATABASE_URL=sqlite:////var/lib/simulador/clinical.db
   GEMINI_API_KEY=sua_chave_privada
   GEMINI_MODEL=gemini-3.5-flash-lite
   ALLOWED_ORIGINS=https://seu-projeto.vercel.app
   ADMIN_USERNAME=admin123
   ADMIN_PASSWORD=uma_senha_longa_e_exclusiva
   ```

   Guarde o arquivo com permissão restrita. A URL SQLite absoluta tem **quatro barras** depois de `sqlite:`. O backend aplica migrações e prepara os casos ao iniciar. O banco nunca deve ficar no disco temporário de contêiner nem em um compartilhamento de rede.
   A senha administrativa acima é apenas um exemplo: substitua-a na VPS, mantenha `.env` fora do Git e reinicie o serviço após alterá-la. A rota `/admin/entrar` da interface usa essas credenciais para consultar contas e avaliações.
4. Crie um serviço `systemd` com `WorkingDirectory=/opt/simulador/backend`, `User=` definido como o usuário que tem acesso ao código e ao banco, `ExecStart=/opt/simulador/backend/.venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000 --workers 1` e `Restart=always`. Não use `--reload` em produção. Verifique `curl http://127.0.0.1:8000/api/health` na VM.
5. Aponte um nome DNS para o IP público da VM e publique HTTPS em 443. Para manter tudo sem custo, um subdomínio gratuito do [Duck DNS](https://www.duckdns.org/about.jsp) pode apontar para o IP da VM. Exemplo de bloco do Caddyfile:

   ```caddyfile
   seu-simulador.duckdns.org {
       reverse_proxy 127.0.0.1:8000
   }
   ```

   Libere 80/443 no firewall da Oracle **e** no firewall do sistema. Mantenha 8000 restrita ao loopback. Confirme `https://seu-simulador.duckdns.org/api/health` externamente. A comunicação da Vercel com a API precisa usar HTTPS. O Caddy obtém o certificado se o DNS apontar para a VM e 80/443 estiverem acessíveis.

## 3. Frontend na Vercel

1. Importe o repositório `Simulador-Clinico-Front-End` como projeto Next.js. Se importar um monorepo, selecione essa pasta como **Root Directory**.
2. Defina no ambiente **Production** `API_BASE_URL=https://seu-simulador.duckdns.org/api`. O `next.config.ts` inclui essa URL no código do navegador; `127.0.0.1` apontaria para o computador do estudante. Não adicione `GEMINI_API_KEY` ao frontend.
3. Faça o deploy. Quando souber a URL final `https://seu-projeto.vercel.app`, coloque-a em `ALLOWED_ORIGINS` no backend e reinicie o serviço. O valor deve ser a **origem exata**, sem `/api` e sem barra final. Se alterar a variável pública da Vercel, gere um novo deployment.
4. Teste no domínio publicado: cadastro, login, dois estudantes em navegadores separados, início do mesmo caso, resposta em streaming, avanço de tempo, conclusão, resultado e feedback. Verifique CORS no console do navegador e os logs do serviço na VPS.

## 4. Antes de divulgar o link

- Adicione limites de requisições por IP/conta para cadastro, login e interações Gemini; ainda não há proteção de rate limit na API. Sem isso, tráfego abusivo pode consumir a cota gratuita da IA e saturar a VM.
- Faça backup consistente com `sqlite3 /var/lib/simulador/clinical.db '.backup /caminho/seguro/clinical-backup.db'`, copie para outro local e teste uma restauração. WAL cria arquivos auxiliares `-wal` e `-shm`; não copie apenas o `.db` ativo com `cp`.
- Acompanhe uso de CPU, RAM, disco, erros `database is locked` e limites do Gemini. SQLite em WAL permite leitores em paralelo com uma gravação, mas serializa gravações. Se houver contenção frequente, ou se precisar de mais de um servidor de API, migre para PostgreSQL; Supabase é uma alternativa, mas o plano grátis limita o banco e pode pausar projetos inativos.
- O plano gratuito do Gemini pode usar entradas e saídas para melhorar os produtos do Google. Como o simulador é educacional, instrua os estudantes a usar apenas casos fictícios e não inserir dados pessoais ou de pacientes reais.
- Faça um teste de carga pequeno com 2–10 usuários simulados usando contas distintas e dados fictícios. Isso confirma o seu ambiente real; nenhum plano grátis garante que 500 usuários simultâneos com chamadas Gemini funcionarão.

Fontes de limites atuais: [Oracle Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), [Vercel Hobby](https://vercel.com/docs/plans/hobby), [Supabase Free](https://supabase.com/pricing), [SQLite WAL](https://www.sqlite.org/wal.html), [Gemini preços](https://ai.google.dev/gemini-api/docs/pricing), [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) e [Caddy HTTPS](https://caddyserver.com/docs/quick-starts/reverse-proxy).
