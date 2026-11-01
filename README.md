<img width="1873" height="988" alt="3" src="https://github.com/user-attachments/assets/69bbfff0-27ee-4e93-ac32-0e8a55b2afea" /># Cloud Builders: deploy no OpenShift com HPA e Persistent Volume

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
    ├── buildconfig.yaml   # build Docker a partir deste repositório
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

oc apply -f manifests/          # cria todos os recursos no projeto atual
oc get builds -w                # aguarde o status Complete (Ctrl+C para sair)
oc rollout status deployment/meu-app
oc get route meu-app            # URL pública da aplicação
```

O `BuildConfig` inicia o primeiro build automaticamente. Quando a imagem é publicada, o Deployment é atualizado pelo trigger de ImageStream. Nesse intervalo os pods podem ficar brevemente em `ErrImagePull`, o que é esperado.

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

<img width="1861" height="976" alt="2" src="https://github.com/user-attachments/assets/9bbd0086-c604-45cc-aff1-795042cd7f30" />
<img width="1873" height="988" alt="3" src="https://github.com/user-attachments/assets/92007689-2f48-4d09-af9f-1eedf37ca127" />
<img width="1873" height="1027" alt="10" src="https://github.com/user-attachments/assets/89f7afde-8e25-4af1-8a7b-3194e9d93d51" />
<img width="1873" height="988" alt="8" src="https://github.com/user-attachments/assets/120b1331-bb76-4e6b-9b5c-ec81b71286f8" />
<img width="1873" height="988" alt="9" src="https://github.com/user-attachments/assets/bd94c131-e031-425a-961a-042af5c18a1b" />

## Decisões e limitações

- **Volume RWO e `podAffinity`:** um volume `ReadWriteOnce` só pode ser montado por pods de um mesmo nó. Para o HPA poder criar réplicas sem travar em `ContainerCreating`, o Deployment mantém os pods juntos. Com um storage `ReadWriteMany`, a affinity pode ser removida.
- **Escrita concorrente:** o log de visitas é gravado em modo *append*, o que evita sobrescrita quando mais de um pod escreve no mesmo arquivo.
- **Limites do Sandbox:** a cota de recursos é pequena, por isso o HPA vai de 1 a 3 réplicas e os `requests` são baixos.
- **`replicas` ausente no Deployment:** o número de pods é controlado pelo HPA. Definir o campo faria cada `oc apply` brigar com o autoscaler.

## Limpeza

```bash
oc delete -f manifests/
```

Isso remove também o volume (`meu-app-pvc`) e, com ele, os dados gravados.
