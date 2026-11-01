# Cloud Builders: deploy no OpenShift com HPA e Persistent Volume

Aplicação containerizada de exemplo implantada no **Red Hat OpenShift** (Developer Sandbox), com:

- **Deploy** via build Docker dentro do próprio cluster (BuildConfig + ImageStream);
- **Persistent Volume** (PVC de 1Gi montado em `/data`) para guardar dados entre reinícios;
- **HPA** (Horizontal Pod Autoscaler) escalando de 1 a 3 réplicas conforme o uso de CPU.

## A aplicação

Servidor HTTP em Python (apenas biblioteca padrão), porta `8080`:

| Rota | O que faz |
|---|---|
| `/` | Registra a visita em `/data/visitas.log` (volume persistente) e mostra o nome do pod, o total de visitas e as últimas 5 |
| `/carga` | Consome CPU por 0,5 s. Serve para disparar o HPA |
| `/health` | Retorna `ok`. Usada pelas probes de readiness e liveness |

A imagem usa `ubi9/python-311`, que roda como usuário não-root (exigência do OpenShift).

## Estrutura do repositório

```
.
├── Dockerfile
├── app.py
├── README.md
└── manifests/
    ├── imagestream.yaml   # destino da imagem construída
    ├── buildconfig.yaml   # build Docker a partir deste repositório (+ webhook do GitHub)
    ├── pvc.yaml           # Persistent Volume Claim (1Gi, RWO)
    ├── deployment.yaml    # pods, probes, resources e montagem do volume
    ├── service.yaml       # Service interno na porta 8080
    ├── route.yaml         # URL pública com HTTPS (TLS edge)
    └── hpa.yaml           # autoscaling de 1 a 3 réplicas (CPU 70%)
```

## Como fazer o deploy

Pré-requisito: acesso a um cluster OpenShift (ex.: [Developer Sandbox](https://developers.redhat.com/developer-sandbox)) com o `oc` logado, por exemplo no Web Terminal do console.

```bash
git clone https://github.com/dnmiguel88/Cloud_Builders.git
cd Cloud_Builders

# segredo do webhook do GitHub (fica só no cluster, nunca no repositório)
oc create secret generic meu-app-webhook \
  --from-literal=WebHookSecretKey=$(openssl rand -hex 20)

oc apply -f manifests/          # cria todos os recursos no projeto atual
oc get builds -w                # aguarde o status Complete (Ctrl+C para sair)
oc rollout status deployment/meu-app
oc get route meu-app            # URL pública da aplicação
```

O `BuildConfig` inicia o primeiro build automaticamente. Quando a imagem é publicada, o Deployment é atualizado pelo trigger de ImageStream. Nesse intervalo os pods podem ficar brevemente em `ErrImagePull`, o que é esperado.

## Build automático (webhook do GitHub)

A cada `git push` na branch `main`, o GitHub chama o OpenShift, que inicia um novo build. Como o Deployment tem trigger de ImageStream, a nova imagem entra em *rolling update* sozinha, e o volume persistente mantém os dados.

**1. Libere o endpoint de webhooks para chamadas não autenticadas (somente neste projeto)**

O GitHub chama a API sem login. Sem esta permissão a resposta é `403 Forbidden`:

```bash
oc policy add-role-to-group system:webhook system:unauthenticated
```

Esse papel só dá acesso ao endpoint de webhooks de build, e quem chama ainda precisa conhecer o segredo da URL.

**2. Monte a URL do webhook**

Use o endereço **público** da API (o `oc whoami --show-server` dentro do Web Terminal devolve um endereço interno, que o GitHub não alcança):

```bash
API=$(oc whoami --show-console | sed 's#https://console-openshift-console.apps#https://api#'):6443
NS=$(oc project -q)
SECRET=$(oc get secret meu-app-webhook -o jsonpath='{.data.WebHookSecretKey}' | base64 -d)
echo "$API/apis/build.openshift.io/v1/namespaces/$NS/buildconfigs/meu-app/webhooks/$SECRET/github"
```

**3. Cadastre no GitHub**

Em *Settings → Webhooks → Add webhook*:

| Campo | Valor |
|---|---|
| Payload URL | a URL do passo 2 |
| Content type | `application/json` |
| Secret | vazio (o segredo já está na URL) |
| Events | *Just the push event* |

Confirme em *Recent Deliveries* que a resposta foi bem-sucedida e acompanhe com `oc get builds -w`.

> **Atenção:** a URL do webhook contém o segredo e deve ser tratada como senha. Não a coloque no repositório, em prints ou em documentação. Para trocar o segredo, atualize o Secret (`oc create secret generic meu-app-webhook --from-literal=WebHookSecretKey=$(openssl rand -hex 20) --dry-run=client -o yaml | oc apply -f -`) e gere a URL de novo.

**Se algo falhar**

| Sintoma em *Recent Deliveries* | Causa |
|---|---|
| `failed to connect to host` | O host da URL não é o endereço público da API (por exemplo, `172.30.0.1`) |
| `403 Forbidden` | Falta a permissão do passo 1 |
| `200`, mas nenhum build novo | A branch do push não bate com `spec.source.git.ref` do BuildConfig (`main`) |

## Testes

```bash
URL=https://$(oc get route meu-app -o jsonpath='{.spec.host}')
```

**Persistência (Persistent Volume)**

```bash
curl -s $URL                          # repita algumas vezes: o contador sobe
oc delete pod -l deployment=meu-app   # derruba o pod
oc rollout status deployment/meu-app
curl -s $URL                          # o contador continua de onde parou
```

**Autoscaling (HPA)**

```bash
for i in $(seq 1 6); do (while true; do curl -s $URL/carga > /dev/null; done) & done

oc get hpa meu-app -w                 # acompanhe a CPU e as réplicas
oc get pods -w                        # em outra aba

kill $(jobs -p)                       # pare a carga; depois de alguns minutos o HPA reduz as réplicas
```

## Evidências

<img width="1873" height="988" alt="3" src="https://github.com/user-attachments/assets/9540f3f7-e292-4ce7-99db-6c49bab4bcb0" />
<img width="1873" height="988" alt="3" src="https://github.com/user-attachments/assets/9214f37d-f41a-4341-a793-2279888453f0" />
<img width="1873" height="988" alt="7" src="https://github.com/user-attachments/assets/8a6ec34f-8bde-433e-b400-584f6d3d6a59" />
<img width="1873" height="988" alt="8" src="https://github.com/user-attachments/assets/793a7349-38b3-487a-aead-ab48f0f33cd6" />
<img width="1873" height="988" alt="9" src="https://github.com/user-attachments/assets/a6882dc7-affa-46d9-ac4f-6843aee97586" />
<img width="1873" height="1027" alt="10" src="https://github.com/user-attachments/assets/0e24d5ad-47b6-40ed-bcbd-388a16609acb" />
<img width="1873" height="989" alt="11" src="https://github.com/user-attachments/assets/a652b1fe-c6d1-48f2-93e8-5a15eb4a3a55" />


## Decisões e limitações

- **Volume RWO e `podAffinity`:** um volume `ReadWriteOnce` só pode ser montado por pods de um mesmo nó. Para o HPA poder criar réplicas sem travar em `ContainerCreating`, o Deployment mantém os pods juntos. Com um storage `ReadWriteMany`, a affinity pode ser removida.
- **Escrita concorrente:** o log de visitas é gravado em modo *append*, o que evita sobrescrita quando mais de um pod escreve no mesmo arquivo.
- **Limites do Sandbox:** a cota de recursos é pequena, por isso o HPA vai de 1 a 3 réplicas e os `requests` são baixos.
- **`replicas` ausente no Deployment:** o número de pods é controlado pelo HPA. Definir o campo faria cada `oc apply` brigar com o autoscaler.

- **Segredo do webhook fora do Git:** o `buildconfig.yaml` só referencia o Secret `meu-app-webhook`, que é criado por comando. O repositório é público, então o segredo nunca deve ser versionado.

## Limpeza

```bash
oc delete -f manifests/
oc delete secret meu-app-webhook
```

Isso remove também o volume (`meu-app-pvc`) e, com ele, os dados gravados.
