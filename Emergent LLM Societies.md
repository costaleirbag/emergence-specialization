# Contexto de Pesquisa — Emergência de Estrutura Funcional em Sociedades de LLMs

> **Documento de contexto vivo do projeto**
>
> **Data desta versão:** 7 de agosto de 2026 — revisão pós-campanha staged  
> **Objetivo:** preservar, em um único arquivo, a motivação científica, a matemática, o desenho experimental, os resultados exploratórios, as hipóteses, as ideias de modelagem e as perguntas críticas que surgiram até aqui.
>
> Este documento foi escrito para ser legível no VS Code, Obsidian e renderizadores Markdown com suporte a MathJax/KaTeX. Fórmulas inline usam `$...$` e fórmulas em bloco usam cercas `math`.

---

## 0. Como usar este documento

Este arquivo deve funcionar de três maneiras:

1. **Contexto para futuras conversas com ChatGPT/Codex:** ao iniciar uma nova sessão, peça para ler este documento antes de discutir o projeto.
2. **Documento de conversa com o orientador:** as seções sobre motivação, matemática, definição de estrutura funcional e perguntas/respostas foram escritas para sustentar uma discussão técnica.
3. **Mapa do projeto científico:** separa claramente o que vem do paper original, o que já foi observado no piloto, o que é hipótese e o que é uma proposta matemática ainda não validada.

Uma regra importante para futuras conversas:

> Não tratar hipóteses, analogias físicas ou modelos mínimos propostos neste documento como resultados já demonstrados.

---


> [!IMPORTANT]
> ## Estado canônico desta revisão
>
> Este arquivo preserva as seções históricas do documento anterior, mas **os detalhes operacionais antigos são superseded pelo Addendum “Estado Atual da Pesquisa e da Campanha” no final do arquivo**.
>
> Em particular, a versão atual já incorpora conceitualmente:
>
> - campanha `developmental-dynamics-v1` staged, resumable e human-gated;
> - Gate 1 com 10 pares private/shared;
> - Gate 2 bloqueado até revisão humana;
> - DeepSeek Direct como caminho atual da campanha (não OMP);
> - checkpoints $t\in\{0,10,20\}$;
> - $560$ logical completions por run baseline;
> - $\Phi(t)$ como parâmetro de diferenciação de competência;
> - análise espectral e $d_{\mathrm{eff}}$;
> - distinção explícita entre HSE, competência, allocation, alignment e utility;
> - random routing e long horizon como **experimentos candidatos**, não etapas automáticas;
> - snapshot intermediário do seed 3 enquanto Gate 1 estava em execução.
>
> **Regra de leitura:** para conceitos e matemática, o documento inteiro é útil. Para “o que está rodando agora?”, leia primeiro o Addendum final.


# 1. A ideia central em uma frase

O paper **When is Routing Meaningful? Diversity and Robustness in Language Model Societies** mede a estrutura comportamental de uma sociedade de modelos essencialmente dada por meio de um behavioral matrix $B$.

A extensão central deste projeto é:

```math
\boxed{B \longrightarrow B(t)}
```

Ou seja:

> **em vez de perguntar apenas quão diversa é uma sociedade, queremos estudar como uma sociedade inicialmente homogênea desenvolve — ou não — estrutura comportamental e funcional ao longo do tempo.**

A pergunta mais ambiciosa é:

```math
\boxed{
\text{quando uma sociedade inicialmente simétrica desenvolve estrutura funcional,
e que estrutura é essa?}
}
```

---

# 2. De onde veio a pergunta

O ponto de partida foi o paper:

> Fantine Huot, Michael Kaisers, Mirella Lapata.  
> **When is Routing Meaningful? Diversity and Robustness in Language Model Societies**.  
> arXiv:2607.09197, 2026.

A crítica central do paper é que routing em sistemas de múltiplos modelos é frequentemente avaliado apenas por:

- task accuracy;
- inference cost;
- custo/qualidade;
- capacidade de selecionar o modelo que produz a melhor resposta.

Os autores argumentam que existem propriedades estruturais adicionais.

Se todos os atores disponíveis produzem praticamente o mesmo comportamento, escolher entre eles é quase vacúo.

E se pequenas reformulações semanticamente equivalentes de uma query fazem o router trocar arbitrariamente de ator, não existe uma distribuição estável de trabalho.

A decomposição conceitual do paper é aproximadamente:

```text
sociedade de atores
       |
       +---- existe diversidade comportamental? -------- HSE
       |
       +---- o routing é estável a perturbações? ------- robustness
```

O paper não afirma que essas propriedades substituem performance. Elas são apresentadas como propriedades **ortogonais** à performance.

Foi daí que surgiu a inversão:

```text
paper:
diversidade existente
        ↓
router pode explorar diferenças

nossa pergunta:
routing / experiência
        ↓
diferenças podem aparecer
        ↓
router passa a encontrar uma sociedade que ele próprio ajudou a produzir
```

Uma formulação que resume a intuição é:

> **The routing mechanism may not merely exploit actor diversity; through asymmetric experience, it may become a generator of the diversity it later exploits.**

---

# 3. O paper original: explicação do nível pedestre ao técnico

## 3.1 O problema mais simples

Considere uma sociedade com atores

```math
\mathcal R = \{r_1,\ldots,r_N\}.
```

Um router é uma função

```math
\pi : \mathcal Q \to \mathcal R,
```

que recebe uma query $q$ e escolhe um ator:

```math
\pi(q)=r_i.
```

Se todos os atores respondem da mesma maneira, então escolher entre eles não acrescenta muito.

O primeiro problema é, portanto:

> Como medir quantitativamente se os atores realmente são comportamentalmente diferentes?

---

## 3.2 Behavioral vectors

O paper evita comparar pesos dos modelos.

Isso é importante porque uma sociedade pode conter:

- modelos de arquiteturas diferentes;
- modelos de escalas diferentes;
- diferentes system prompts;
- agentes com ferramentas distintas;
- diferentes configurações.

Em vez disso, todos são avaliados em um conjunto comum:

```math
\mathcal E = \{e_1,\ldots,e_L\}.
```

Para o ator $r_i$, define-se:

```math
b_i =
\left(
s(r_i,e_1),
s(r_i,e_2),
\ldots,
s(r_i,e_L)
\right)
\in \mathbb R^L,
```

onde:

```math
s(r_i,e_\ell)\in[0,1]
```

é o score do ator $i$ no item $\ell$.

No caso binário:

```math
s(r_i,e_\ell)\in\{0,1\}.
```

Exemplo:

```math
b_1=(1,1,0,0,1),
```

```math
b_2=(1,1,0,0,1),
```

```math
b_3=(0,0,1,1,0).
```

Os atores 1 e 2 têm o mesmo perfil de sucesso e erro. O ator 3 é comportamentalmente diferente.

---

## 3.3 Behavioral matrix

Empilhando os vetores:

```math
B =
\begin{bmatrix}
b_1^\top\\
b_2^\top\\
\vdots\\
b_N^\top
\end{bmatrix}
\in\mathbb R^{N\times L}.
```

Esse é o **behavioral matrix**.

Ele representa uma sociedade no espaço de comportamentos observados.

Uma ideia central do paper é:

> diferenças em parameter space não são necessariamente diferenças em behavioral space.

Isso também permite aplicar a mesma análise a atores que compartilham exatamente os mesmos pesos, desde que seus estados/prompt/memórias produzam comportamentos diferentes.

---

# 4. Distância comportamental

O paper usa cosine distance:

```math
d(r_i,r_j)
=
1-
\frac{
b_i^\top b_j
}{
\|b_i\|_2\|b_j\|_2
}.
```

A intenção é comparar o **perfil** de acertos e erros, e não simplesmente accuracy absoluta.

Dois agentes podem ter accuracy semelhante e ainda assim errar itens completamente diferentes.

Esses dois casos são estruturalmente diferentes:

### Caso 1 — redundância

```math
b_1=(1,1,0,0),
```

```math
b_2=(1,1,0,0).
```

### Caso 2 — complementaridade

```math
b_1=(1,1,0,0),
```

```math
b_2=(0,0,1,1).
```

No segundo caso, existe muito mais estrutura potencial para routing.

O paper define distância máxima quando um dos vetores tem norma zero, isto é, quando um ator falha em todo o evaluation set.

---

# 5. Shannon entropy e Simple Social Entropy

Suponha que uma partição comportamental da sociedade tenha clusters

```math
\mathcal C=\{c_1,\ldots,c_M\}.
```

Se:

```math
p_k = \frac{|c_k|}{N},
```

então a simple social entropy é:

```math
H(\mathcal R)
=
-\sum_{k=1}^M p_k\log_2p_k.
```

Se todo mundo está no mesmo grupo:

```math
H=0.
```

Se existem $N$ grupos de tamanho igual:

```math
H=\log_2N.
```

O problema é que isso considera somente:

- número de grupos;
- proporção de atores em cada grupo.

Ela não considera **quão distantes** esses grupos estão.

---

# 6. Por que Hierarchic Social Entropy?

Considere uma sociedade com:

- três atores praticamente idênticos;
- um outlier.

A partição $3+1$ produz:

```math
H
=
-\frac34\log_2\frac34
-\frac14\log_2\frac14
\approx0.811.
```

Isso vale tanto se o outlier estiver muito próximo quanto muito distante.

Mas intuitivamente:

```text
sociedade A
● ● ●   ○

sociedade B
● ● ●                                ○
```

não deveriam receber a mesma medida de diversidade.

A HSE resolve isso avaliando a sociedade em **múltiplas escalas de resolução**.

---

# 7. O que significa “Hierarchic” em HSE

“Hierarchic” não significa que existe uma hierarquia social entre os agentes.

Significa que a sociedade é observada em vários níveis de resolução de um clustering hierárquico.

Usando single-linkage, um threshold $h$ determina quando clusters se fundem.

Para cada $h$, obtemos uma partição:

```math
\mathcal C(h).
```

E calculamos:

```math
H(\mathcal R,h)
=
-\sum_{c\in\mathcal C(h)}
p_c(h)\log_2p_c(h).
```

Quando $h$ é muito pequeno, atores diferentes ficam separados.

Conforme $h$ aumenta, clusters semelhantes são fundidos.

No limite:

```math
h\to\infty
\quad\Rightarrow\quad
H(\mathcal R,h)\to0.
```

---

# 8. A HSE como uma área

A definição é:

```math
\boxed{
\mathrm{HSE}(\mathcal R)
=
\int_0^\infty H(\mathcal R,h)\,dh
}
```

Como a partição muda somente nos merge heights do dendrograma, na implementação essa integral pode ser computada como uma soma finita.

A interpretação geométrica é:

> **HSE é a área sob a curva de entropia da sociedade ao variar a resolução taxonômica.**

Ela aumenta quando:

- existem vários grupos;
- esses grupos têm tamanhos relevantes;
- os grupos permanecem separados por uma grande faixa de thresholds.

---

# 9. Exemplo matemático simples da HSE

Considere novamente uma sociedade $3+1$.

Suponha que o outlier esteja a distância $d$ do cluster principal.

Até $h<d$:

```math
H(h)=0.811.
```

Depois que $h\ge d$, todos viram um único cluster:

```math
H(h)=0.
```

Então:

```math
\mathrm{HSE}
=
\int_0^d0.811\,dh
=
0.811d.
```

Essa conta resume bem a ideia:

```math
\boxed{
\text{HSE combina diversidade de grupos com separação comportamental}
}
```

---

# 10. Sanity check: perfis ortogonais

Considere:

```math
b_1=(1,0,0),
```

```math
b_2=(0,1,0),
```

```math
b_3=(0,0,1).
```

As cosine distances são máximas:

```math
d_{ij}=1.
```

Para $0\le h<1$, temos três clusters unitários:

```math
H(h)=\log_2 3.
```

Portanto:

```math
\mathrm{HSE}=\log_2 3\approx1.585.
```

No paper, a HSE normalizada desse caso é $1$.

No setup atual, com distâncias máximas em $1$, uma normalização natural é:

```math
\mathrm{HSE}_{\mathrm{norm}}
=
\frac{\mathrm{HSE}}{\log_2N}.
```

A implementação deve sempre ser conferida contra os sanity checks do paper.

---

# 11. Routing robustness no paper

A segunda quantidade principal do paper é a robustez do routing.

Para uma query $q_i$:

```math
a_i=\pi(q_i).
```

Geramos perturbações semanticamente equivalentes:

```math
\tilde q_i^{(1)},\ldots,\tilde q_i^{(p)}.
```

A robustez por query é:

```math
\rho_i
=
\frac1p
\sum_{j=1}^p
\mathbf 1
\left[
\pi(\tilde q_i^{(j)})=a_i
\right].
```

A robustez total:

```math
\rho
=
\frac1n\sum_{i=1}^n\rho_i.
```

A interpretação é:

> Queries semanticamente equivalentes são encaminhadas de maneira estável para o mesmo ator?

---

# 12. Uma sutileza importante da robustez

Considere um router degenerado:

```math
\pi(q)=r_1
\qquad\forall q.
```

Ele sempre escolhe o mesmo ator.

Então:

```math
\rho=1.
```

Logo:

```math
\boxed{
\text{routing robustness}
\neq
\text{boa divisão de trabalho}
}
```

Robustez mede estabilidade, não utilidade.

O próprio paper é explícito:

> estabilidade do routing é uma condição necessária para especialização estável, mas não é afirmado que routing estável produza especialização.

---

# 13. O paper prova que mais diversidade melhora performance?

## Resposta curta

**Não.**

Essa é uma pergunta que provavelmente surgirá numa conversa com o orientador.

A contribuição do paper não é:

```math
\mathrm{HSE}\uparrow
\quad\Rightarrow\quad
\mathrm{accuracy}\uparrow.
```

Os autores tratam HSE e robustness como propriedades estruturais **ortogonais** à task accuracy.

O paper inclusive diz explicitamente que não assume que diversidade seja sempre desejável; em certas tarefas, sociedades homogêneas podem ser melhores.

### O que eles observam empiricamente

Em sociedades sintéticas de especialistas, a HSE é maior que em pools de modelos reais de tamanho equivalente.

Em alguns experimentos:

- routers KNN ganham clean-query accuracy quando HSE aumenta;
- porém sua robustness sob perturbações pode piorar drasticamente;
- prompted routing mantém maior estabilidade.

Ou seja:

```math
\text{clean accuracy}
\quad\text{e}\quad
\text{meaningfulness/robustness}
```

podem divergir.

### Resultado especialmente relevante

No apêndice de model selection, o paper compara:

- selecionar subsets maximizando HSE;
- selecionar subsets maximizando HSE conjuntamente com task accuracy.

Eles encontram um **diversity–accuracy trade-off**:

> subsets selecionados apenas por HSE têm maior HSE, mas menor routing task accuracy.

Quando accuracy entra no critério de seleção, performance melhora, embora com alguma perda de HSE.

Portanto:

```math
\boxed{
\text{mais diversidade, sozinha, não é garantia de melhor performance}
}
```

Essa distinção é central para o nosso projeto.

---

# 14. Qual é exatamente a abertura que o paper deixa?

Na seção de limitações, os autores dizem que:

- HSE depende de um evaluation set fixo e pode ser enganosa se esse conjunto não for representativo;
- suas sociedades sintéticas têm perfis muito mais nítidos que especialistas reais;
- routing robustness é medido em single-turn assignment;
- a métrica não captura se atores **desenvolvem competência especializada** como consequência das distribuições estáveis de queries que recebem.

Eles citam como direções naturais:

- multi-step agentic settings;
- usar HSE como training signal;
- bootstrap de sociedades diversas a partir de homogeneous initialization.

Nosso projeto é inspirado justamente nesse espaço, mas não é uma reprodução do paper.

---

# 15. A nossa inversão: $B\to B(t)$

No paper:

```math
B
```

é um snapshot de uma sociedade.

Nós queremos observar:

```math
B(0),B(1),\ldots,B(T).
```

Para o agente $i$ no tempo $t$:

```math
b_i(t)
=
\left(
s(r_i(t),e_1),
\ldots,
s(r_i(t),e_L)
\right).
```

E:

```math
\boxed{
B(t)
=
\begin{bmatrix}
b_1(t)^\top\\
\vdots\\
b_N(t)^\top
\end{bmatrix}
}
```

A variável científica passa a ser a **trajetória no espaço comportamental**.

---

# 16. O que significa “agentes homogêneos”?

É melhor dizer **identically configured / exchangeable**, e não “outputs idênticos”.

Inicialmente, todos têm:

- mesmo modelo;
- mesmos pesos;
- mesmo system prompt;
- mesmas capacidades;
- mesma política de memória;
- memória vazia;
- nenhuma role atribuída;
- IDs opacos somente no host.

Por causa do stochastic decoding, dois agentes podem produzir respostas diferentes mesmo no tempo zero.

Então:

```math
b_i(0)\neq b_j(0)
```

pode ocorrer por ruído.

A simetria importante é de distribuição:

```math
r_i(0)\overset{d}=r_j(0).
```

---

# 17. Por que HSE no tempo zero pode ser não nula?

Por stochasticity.

Mesmo sem diferença de experiência:

```math
b_i(0)
```

e

```math
b_j(0)
```

podem conter acertos e erros diferentes.

Então:

```math
\mathrm{HSE}(0)>0
```

não implica nenhuma especialização.

Por isso uma quantidade melhor é:

```math
\Delta\mathrm{HSE}(t)
=
\mathrm{HSE}(t)-\mathrm{HSE}(0),
```

e principalmente o contraste pareado:

```math
D_s(t)
=
\Delta\mathrm{HSE}_{\mathrm{private},s}(t)
-
\Delta\mathrm{HSE}_{\mathrm{shared},s}(t).
```

---

# 18. O experimento sintético atual

A sociedade tem:

```math
N=4
```

agentes e quatro hidden worlds.

Cada mundo implementa uma regra modular:

```math
f_c(x,y)
=
(a_cx+b_cy+c_c)\bmod7.
```

As regras usadas no experimento devem ser verificadas diretamente no código congelado antes de qualquer novo batch.

A versão atual pretendida é:

```math
f_{\mathrm{ALPHA}}(x,y)
=
(2x+y+1)\bmod7,
```

```math
f_{\mathrm{BETA}}(x,y)
=
(x+3y+2)\bmod7,
```

```math
f_{\mathrm{GAMMA}}(x,y)
=
(4x+2y+3)\bmod7,
```

```math
f_{\mathrm{DELTA}}(x,y)
=
(3x+5y+4)\bmod7.
```

> **Nota de provenance:** uma versão inicial da documentação omitiu o termo `+3` de GAMMA. Para resultados futuros, o código/version hash deve ser a fonte final da verdade.

A intenção não é que essas funções sejam “tarefas realistas”.

Elas são um **organismo experimental mínimo**:

- mesma complexidade estrutural;
- regras diferentes;
- ground truth exato;
- expertise adquirível dentro da run;
- baixa contaminação por conhecimento de pretraining.

---

# 19. O loop de interação

No round $t$:

1. escolhe-se um mundo $C_t$;
2. amostra-se $(x_t,y_t)$;
3. todos os agentes recebem a mesma tarefa;
4. cada agente produz resposta $Y_{it}$ e confidence $Q_{it}$;
5. o router escolhe um agente;
6. o ambiente avalia a resposta selecionada;
7. o feedback é distribuído conforme a condição;
8. memórias são atualizadas.

O baseline de routing é:

```math
R_t
=
\arg\max_iQ_{it},
```

com desempate aleatório controlado.

A confidence não é interpretada como probabilidade calibrada.

Ela é um componente da dinâmica.

---

# 20. Private versus Shared

## 20.1 Private

Somente o agente selecionado recebe a experiência/feedback.

Então:

```math
M_i(t)\neq M_j(t)
```

pode aparecer rapidamente.

O loop candidato é:

```math
\text{experiência}
\to
\text{competência}
\to
\text{confidence}
\to
\text{seleção}
\to
\text{mais experiência}.
```

## 20.2 Shared

O outcome do round é copiado para todos.

Todos permanecem expostos essencialmente ao mesmo histórico informacional.

A comparação não deve ser lida como:

> “private é melhor”.

Ela é uma manipulação de **localidade da informação**.

O objetivo é permitir ou suprimir divergência endógena de trajetória.

---

# 21. Como avaliamos a sociedade sem contaminá-la

Nos checkpoints, congelamos as memórias e aplicamos o mesmo fixed probe set a todos.

Os probes:

- são idênticos para todos;
- não atualizam memória;
- não são usados para learning;
- devem ser held-out em relação às experiências normais.

Isso produz:

```math
B(t).
```

Para estudar competência por mundo, também construímos:

```math
A(t)\in[0,1]^{N\times K},
```

onde:

```math
\boxed{
A_{ic}(t)
=
P(\text{agente }i\text{ acerta}\mid C=c,t)
}
```

estimado por probes.

---

# 22. A pergunta crítica: o que significa “desenvolver estrutura funcional”?

Essa expressão precisa ser operacionalizada.

Não basta:

```math
\mathrm{HSE}\uparrow.
```

Propomos separar vários níveis.

## 22.1 Nível 0 — diferenciação comportamental

Os agentes passaram a produzir perfis diferentes?

Medidas:

- HSE;
- distância entre $b_i$;
- parâmetro de ordem $\Phi$ definido adiante.

Isso responde:

> Eles diferiram?

Não responde:

> A diferença serve para alguma coisa?

## 22.2 Nível 1 — estrutura task-dependent

O domínio da tarefa informa qual agente é selecionado?

Defina:

```math
C=\text{tipo/mundo da tarefa},
```

```math
R=\text{agente selecionado}.
```

Então:

```math
I(C;R)
=
\sum_{c,r}
p(c,r)
\log_2
\frac{p(c,r)}{p(c)p(r)}.
```

Se:

```math
I(C;R)>0,
```

existe associação entre task type e selected agent.

Mas isso ainda pode ser uma associação ruim.

## 22.3 Nível 2 — competence specialization

Os agentes ficaram bons em coisas diferentes?

Isso aparece em:

```math
A_{ic}(t).
```

Um padrão idealizado, depois de permutar labels, seria:

```math
A(t)
\approx
\begin{bmatrix}
1&0&0&0\\
0&1&0&0\\
0&0&1&0\\
0&0&0&1
\end{bmatrix}.
```

Mas perfis reais serão mais suaves e sobrepostos.

## 22.4 Nível 3 — routing alinhado à competência

É possível ter:

```math
I(C;R)>0
```

e ainda encaminhar cada mundo para o agente errado.

Então precisamos perguntar:

> O router explora a competência que existe?

Defina:

```math
P_t(R=i\mid C=c).
```

A utilidade estrutural esperada do routing é:

```math
\boxed{
U_{\mathrm{route}}(t)
=
\sum_c p(c)
\sum_i
P_t(R=i\mid C=c)A_{ic}(t)
}
```

Um baseline uniforme é:

```math
U_{\mathrm{rand}}(t)
=
\sum_c p(c)\bar A_c(t),
```

onde:

```math
\bar A_c(t)
=
\frac1N\sum_iA_{ic}(t).
```

O melhor routing por domínio seria:

```math
U_{\mathrm{oracle-domain}}(t)
=
\sum_c p(c)\max_iA_{ic}(t).
```

Quando o denominador é positivo, podemos definir:

```math
\boxed{
\eta_{\mathrm{route}}(t)
=
\frac{
U_{\mathrm{route}}(t)-U_{\mathrm{rand}}(t)
}{
U_{\mathrm{oracle-domain}}(t)-U_{\mathrm{rand}}(t)
}
}
```

Interpretação:

- $\eta_{\mathrm{route}}\approx0$: o router não explora a estrutura disponível;
- $\eta_{\mathrm{route}}\approx1$: ele captura quase todo o ganho de alocação por domínio;
- $\eta_{\mathrm{route}}<0$: ele encaminha sistematicamente pior que o baseline.

## 22.5 Nível 4 — complementaridade da sociedade

Melhor indivíduo:

```math
A_{\mathrm{best}}
=
\max_i
\frac1L
\sum_{\ell=1}^Ls_{i\ell}.
```

Oracle por item:

```math
A_{\mathrm{oracle}}
=
\frac1L
\sum_{\ell=1}^L
\mathbf 1
\left[
\exists i:s_{i\ell}=1
\right].
```

Oracle gain:

```math
\boxed{
\Delta_{\mathrm{comp}}
=
A_{\mathrm{oracle}}-A_{\mathrm{best}}
}
```

Isso mede potencial coletivo, não performance real do router.

## 22.6 Nível 5 — estabilidade e robustez

Uma role só é convincente se persistir.

Podemos medir:

- estabilidade temporal do competence profile;
- estabilidade da associação task $\to$ agent;
- routing robustness a paráfrases;
- tempo de permanência em uma role;
- turnover.

## 22.7 Nível 6 — performance coletiva real

Finalmente:

> O sistema roteado resolve tarefas melhor?

A accuracy real do sistema é:

```math
\boxed{
A_{\mathrm{team}}
=
\frac1T
\sum_{t=1}^T
\mathbf 1
\left[
Y_{R_t,t}=Y_t^\star
\right]
}
```

Essa é uma quantidade diferente de HSE, MI e oracle gain.

---

# 23. Uma definição operacional de “estrutura funcional”

Uma definição útil para o projeto é:

> **A sociedade desenvolveu estrutura funcional quando a diferenciação adquirida deixa de ser apenas ruído e passa a organizar competência e alocação de trabalho de forma task-dependent, persistente e potencialmente útil.**

Operacionalmente, uma evidência forte envolveria conjuntamente:

1. diferenciação acima do baseline/control;
2. matriz de competência estruturada;
3. associação task–agent;
4. routing alinhado à competência;
5. persistência/robustez;
6. ganho coletivo real ou potencial.

Em símbolos, queremos distinguir:

```math
\text{diferenciação}
```

de:

```math
\text{especialização}
```

de:

```math
\text{especialização útil}
```

de:

```math
\text{coordenação eficiente}.
```

---

# 24. Uma métrica elegante para “divisão de trabalho potencial”

Se $N=K$, podemos perguntar qual seria a melhor atribuição um-para-um entre agentes e mundos.

Considere o grupo de permutações $S_N$.

Defina:

```math
\boxed{
U_{\mathrm{match}}(t)
=
\max_{\sigma\in S_N}
\frac1K
\sum_{c=1}^K
A_{\sigma(c),c}(t)
}
```

Isso pode ser computado como um assignment problem/Hungarian matching.

Compare com o melhor agente generalista:

```math
U_{\mathrm{single}}
=
\max_i
\frac1K\sum_cA_{ic}.
```

Então:

```math
\Delta_{\mathrm{match}}
=
U_{\mathrm{match}}-U_{\mathrm{single}}.
```

Interpretação:

> Existe uma decomposição funcional da sociedade em que diferentes indivíduos cobririam diferentes niches melhor que qualquer indivíduo sozinho?

Para $N\neq K$, a ideia pode ser generalizada para matching/capacity-constrained assignment.

---

# 25. No final, vamos avaliar em que tarefa?

## 25.1 Primeira fase: hidden-world held-out tasks

A primeira tarefa de avaliação deve continuar sendo o mesmo tipo de sistema procedural, mas com inputs held-out.

Treinamos/adaptamos a sociedade através de interações em quatro regras escondidas.

No evaluation:

- congelamos memória;
- geramos novos $(x,y)$;
- mantemos os mesmos hidden worlds;
- observamos cada agente, o router e a sociedade.

Isso testa se a experiência adquirida generaliza dentro de cada regra.

## 25.2 O resultado coletivo principal

O sistema realmente executado é:

```math
q
\to
\text{todos produzem confidence/answer}
\to
R
\to
\text{resposta selecionada}.
```

Então a performance coletiva relevante é a accuracy da **resposta roteada**.

Baselines importantes:

- melhor single agent;
- average single agent;
- uniform random routing;
- shared condition;
- static/no-learning control;
- oracle por domínio;
- oracle por item.

## 25.3 É obrigatório colocar os agentes para colaborar?

**Não para a pergunta atual.**

O paper de origem é sobre **routing / task allocation**, não sobre deliberative collaboration.

Nosso sistema é uma sociedade adaptativa mediada por assignment.

Se colocarmos os agentes para conversar, votar e revisar respostas agora, introduzimos:

- communication;
- persuasion;
- consensus;
- information aggregation;
- social influence.

Isso é interessante, mas muda a pergunta.

## 25.4 Quando colaboração deve entrar

Uma segunda etapa mais forte pode usar tarefas que exigem múltiplas subcompetências.

Exemplo:

```math
q=(q_A,q_B,q_C),
```

onde diferentes subtarefas dependem de regras/skills diferentes.

A sociedade poderia:

1. decompor;
2. alocar subtarefas;
3. integrar resultados.

Aí a pergunta vira:

> a estrutura funcional emergente melhora collective task performance quando uma tarefa realmente exige competências distribuídas?

---

# 26. O modelo matemático da sociedade como processo estocástico

Defina o estado experimental:

```math
S_t
=
\left(
M_1(t),\ldots,M_N(t)
\right).
```

A tarefa no tempo $t$ é:

```math
Z_t=(C_t,X_t).
```

Cada agente produz:

```math
(Y_{it},Q_{it})
\sim
P_\theta
\left(
\cdot\mid Z_t,M_i(t)
\right).
```

O router escolhe:

```math
R_t
=
g(Q_{1t},\ldots,Q_{Nt}).
```

Depois o estado muda.

Podemos representar isso abstratamente como:

```math
\boxed{
S_{t+1}
\sim
K_\lambda(
\cdot\mid
S_t,Z_t
)
}
```

onde $\lambda$ codifica a localidade/privacidade do feedback.

---

# 27. Exchangeability e permutation equivariance

Os labels dos agentes são arbitrários.

Se $\sigma\in S_N$ é uma permutação dos agentes, queremos que o sistema seja simétrico sob relabeling.

Inicialmente:

```math
P_\sigma S_0
\overset d=
S_0.
```

Idealmente, a dinâmica é permutation-equivariant:

```math
K(P_\sigma S'\mid P_\sigma S)
=
K(S'\mid S).
```

Então a distribuição do ensemble preserva a simetria:

```math
S_t
\overset d=
P_\sigma S_t.
```

Mas uma trajetória particular pode ficar fortemente assimétrica.

Essa é a assinatura conceitual:

```math
\boxed{
\text{ensemble symmetry}
+
\text{within-run asymmetry}
}
```

---

# 28. O que significaria symmetry breaking aqui?

Com $N=4$, devemos ser cuidadosos.

Não estamos automaticamente falando de spontaneous symmetry breaking no sentido termodinâmico de:

```math
N\to\infty.
```

Uma linguagem mais defensável inicialmente é:

- finite-system symmetry breaking;
- trajectory-level spontaneous asymmetry;
- spontaneous differentiation under exchangeable initial conditions.

Uma assinatura forte seria:

```text
seed 1 → agent_2 ocupa um niche
seed 2 → agent_0 ocupa o mesmo niche
seed 3 → agent_3 ocupa o niche
...
```

Dentro da run há assimetria.

No ensemble:

```math
P(\text{label }i\text{ ocupa role }c)
\approx
\frac1N.
```

---

# 29. Um parâmetro de ordem simples a partir de $A(t)$

HSE conecta diretamente ao paper, mas podemos definir uma quantidade mais analítica.

A competência média da sociedade no mundo $c$ é:

```math
\bar A_c(t)
=
\frac1N\sum_iA_{ic}(t).
```

Defina:

```math
X_{ic}(t)
=
A_{ic}(t)-\bar A_c(t).
```

Então:

```math
\boxed{
\Phi(t)
=
\frac1{NK}
\|X(t)\|_F^2
}
```

ou equivalentemente:

```math
\Phi(t)
=
\frac1K
\sum_c
\mathrm{Var}_i[A_{ic}(t)].
```

Se todos têm o mesmo perfil:

```math
\Phi=0.
```

Se competências divergem:

```math
\Phi>0.
```

Propriedades desejáveis:

- interpretável;
- permutation-invariant;
- não depende do label do agente;
- separa claramente diferença de competence.

Mas $\Phi>0$ ainda não implica utilidade.

---

# 30. Espectro da estrutura funcional

A matriz centralizada é:

```math
X
=
A-\mathbf 1\bar A^\top.
```

Podemos construir:

```math
Q
=
\frac1KXX^\top,
```

uma matriz de overlap/covariância entre agentes.

Ou:

```math
C
=
\frac1NX^\top X,
```

no espaço de nichos.

Os autovalores:

```math
\lambda_1,\lambda_2,\ldots
```

mostram quantos modos independentes de diferenciação existem.

Um participation ratio natural é:

```math
\boxed{
d_{\mathrm{eff}}
=
\frac{
\left(\sum_j\lambda_j\right)^2
}{
\sum_j\lambda_j^2
}
}
```

Intuição:

- $d_{\mathrm{eff}}\approx1$: assimetria essencialmente unidimensional;
- $d_{\mathrm{eff}}>1$: múltiplos eixos de diferenciação/niches.

Isso pode ajudar a distinguir winner-take-all de multidimensional division of labor.

---

# 31. O plano $H(R)\times I(C;R)$

Defina utilization entropy:

```math
H(R)
=
-\sum_iP(R=i)\log_2P(R=i).
```

Normalização:

```math
H_{\mathrm{util}}
=
\frac{H(R)}{\log_2N}.
```

Combine com $I(C;R)$.

| Regime | $H(R)$ | $I(C;R)$ |
|---|---:|---:|
| um agente faz tudo | baixo | baixo |
| roteamento balanceado aleatório | alto | baixo |
| divisão de trabalho task-specific | alto/intermediário | alto |
| roteamento task-specific desigual | intermediário | alto |

Esse plano pode se tornar uma representação de regimes de alocação.

---

# 32. O problema de MI com poucas observações

Com:

```math
T=20
```

e uma tabela $4\times4$, o plug-in estimator de MI tem viés positivo.

Então não devemos interpretar $I(C;R)>0$ sozinho como evidência.

A análise preparada inclui:

- permutation null;
- null mean;
- permutation percentile/p-value diagnóstico;
- excess MI:

```math
I_{\mathrm{excess}}
=
I_{\mathrm{obs}}
-
E[I_{\mathrm{perm}}].
```

O ideal também é aumentar o número de decisões.

---

# 33. Modelagem mínima: memória como ponto em um simplex

Suponha $K$ niches/worlds.

Defina para cada agente:

```math
x_i(t)
=
(x_{i1},\ldots,x_{iK}),
```

onde $x_{ic}$ representa a fração da memória/capacidade do agente dedicada ao mundo $c$.

Como a memória é finita:

```math
x_{ic}\ge0,
```

e:

```math
\sum_cx_{ic}=1.
```

Logo:

```math
\boxed{
x_i(t)\in\Delta^{K-1}
}
```

A sociedade inteira vive em:

```math
\boxed{
(\Delta^{K-1})^N.
}
```

---

# 34. Por que memória finita pode gerar niche competition?

Se o agente dedica mais capacidade a ALPHA:

```math
x_{i,\mathrm{ALPHA}}\uparrow,
```

a soma precisa continuar em $1$.

Isso força trade-offs.

Então adquirir mais representação de uma família de tarefas pode diminuir a representação relativa de outras.

Isso fornece um mecanismo natural de:

- capacity constraint;
- competition;
- specialization.

Sem um trade-off, reinforcement puro pode simplesmente criar um agente globalmente dominante.

---

# 35. Uma dinâmica aproximada da memória

Uma aproximação suave de uma recent-memory/FIFO pode ser:

```math
x_i(t+1)
=
(1-\alpha)x_i(t)+\alpha e_c
```

quando o agente $i$ recebe uma experiência do mundo $c$.

Aqui $e_c$ é o vetor one-hot do niche.

Isso não é a dinâmica exata do LLM.

É um coarse-grained toy model.

---

# 36. Routing dependente da competência

Suponha que competência/confidence no niche $c$ dependa de:

```math
g(x_{ic}),
```

com $g$ crescente.

Uma política probabilística simples:

```math
p_i(c)
=
P(R=i\mid C=c)
=
\frac{
\exp[\beta g(x_{ic})]
}{
\sum_j\exp[\beta g(x_{jc})]
}.
```

Então aparece o loop:

```math
x_{ic}\uparrow
\Rightarrow
g(x_{ic})\uparrow
\Rightarrow
p_i(c)\uparrow
\Rightarrow
\text{mais tarefas }c
\Rightarrow
x_{ic}\uparrow.
```

---

# 37. Mean-field do regime private

Se os worlds aparecem com probabilidades $\rho_c$, uma dinâmica mean-field possível é:

```math
\boxed{
\dot x_{ic}
=
\eta
\left[
\rho_cp_i(c)
-
x_{ic}
\sum_d\rho_dp_i(d)
\right]
}
```

O primeiro termo representa entrada de experiência no niche $c$.

O segundo impõe conservação/competição associada à capacidade limitada.

Isso produz uma dinâmica não linear acoplada.

---

# 38. Mean-field do regime shared

No limite em que todos recebem todas as experiências, uma aproximação simples é:

```math
\dot x_{ic}
=
\eta(\rho_c-x_{ic}).
```

O fixed point é:

```math
\boxed{
x_{ic}^\star=\rho_c\qquad\forall i.
}
```

Todos convergem para a mesma composição.

Isso fornece uma explicação mínima de por que shared tende a preservar simetria no modelo coarse-grained.

---

# 39. Toy linear stability: amplification de pequenas diferenças

Considere um único score $s_i$ por agente.

Routing:

```math
p_i
=
\frac{e^{\beta s_i}}
{\sum_je^{\beta s_j}}.
```

Uma dinâmica simplificada:

```math
s_i(t+1)
=
s_i(t)
+
\eta
\left[
(1-\lambda)
+
\lambda\mathbf1(R_t=i)
\right].
```

Aqui:

- $\lambda=0$: feedback totalmente shared;
- $\lambda=1$: reinforcement totalmente private.

Em média:

```math
E[\Delta s_i]
=
\eta
\left[
(1-\lambda)+\lambda p_i
\right].
```

Perto do estado simétrico:

```math
s_i=s+\delta_i,
```

com:

```math
\sum_i\delta_i=0.
```

A expansão do softmax dá:

```math
p_i
\approx
\frac1N+\frac{\beta}{N}\delta_i.
```

Então:

```math
\delta_i(t+1)
\approx
\left(
1+\frac{\eta\lambda\beta}{N}
\right)\delta_i(t).
```

Nesse toy model extremamente simples, se:

```math
\eta\lambda\beta>0,
```

pequenas assimetrias são amplificadas.

Isso **não é uma prova sobre o LLM**.

É um mecanismo mínimo que pode gerar uma previsão testável.

---

# 40. Relação com modelos de divisão de trabalho em insetos sociais

A inspiração histórica mais concreta vem de response-threshold/self-reinforcement models.

Em modelos clássicos:

- uma tarefa gera estímulo;
- indivíduos possuem thresholds de resposta;
- indivíduos com threshold menor respondem mais;
- executar uma tarefa pode reduzir o threshold correspondente;
- deixar de executá-la pode aumentar o threshold.

Esse reinforcement pode gerar especialistas a partir de indivíduos inicialmente semelhantes.

A analogia estrutural, sem antropomorfização, é:

| Insetos sociais | Sociedade de LLMs |
|---|---|
| task stimulus | query/task |
| response threshold | propensity/confidence |
| task execution | selection |
| reinforcement | memory/feedback |
| specialization | stable competence/task allocation |

Essa ponte deve ser tratada como inspiração/modeling language, não como identidade entre os sistemas.

---

# 41. Uma conexão possível com processos de urnas reforçadas

O mecanismo:

```math
\text{ser selecionado}
\to
\text{aumentar chance de futura seleção}
```

é parente de reinforced urn / Pólya-like processes.

Isso é útil como referência matemática para:

- path dependence;
- lock-in;
- random symmetry breaking;
- rich-get-richer dynamics.

Não devemos afirmar que o experimento é literalmente uma Pólya urn sem derivar uma correspondência adequada.

---

# 42. Estados possíveis / attractor language

O objetivo da teoria mínima seria estudar possíveis regimes:

```math
\text{symmetric state},
```

```math
\text{winner-take-all},
```

```math
\text{division-of-labor},
```

```math
\text{metastable / switching},
```

```math
\text{weak differentiation}.
```

A pergunta deixa de ser simplesmente:

> os agentes se especializam?

E vira:

```math
\boxed{
\text{qual é a estrutura dos estados estáveis/metastáveis do processo coletivo?}
}
```

---

# 43. Parâmetros de controle potenciais

Depois da replicação básica, podemos estudar:

```math
\lambda=\text{localidade do feedback},
```

```math
\beta=\text{sensibilidade do routing},
```

```math
K_m=\text{capacidade de memória},
```

```math
N=\text{tamanho da população},
```

```math
K=\text{número de niches}.
```

Somente se houver evidência de mudanças qualitativas robustas devemos falar em:

- bifurcação;
- criticality;
- phase transition.

Antes disso, use **regime change**.

---

# 44. O caso $N=K$ e estados degenerados sob permutação

Para $N=K=4$, um estado ideal de especialização é:

```math
A
\approx
\begin{bmatrix}
1&0&0&0\\
0&1&0&0\\
0&0&1&0\\
0&0&0&1
\end{bmatrix}.
```

Mas qualquer permutação das linhas é cientificamente equivalente.

Existem:

```math
4!=24
```

assignments symmetry-related.

A dinâmica não deveria preferir nenhum label específico.

Uma run pode selecionar um deles aleatoriamente.

---

# 45. Learned embeddings e coarse-graining

Uma extensão interessante é aprender uma representação mais rica do estado funcional de cada agente.

Mas ela deve ficar **do lado do observador**, não participar do routing/feedback do experimento baseline.

A cadeia conceitual seria:

```math
\boxed{
\text{microstate/history}
\to
A_i(t)
\to
z_i(t)
}
```

onde:

- $M_i(t)$ e histórico completo são o microstate;
- $A_i(t)$ é um fenótipo interpretável;
- $z_i(t)$ é um learned macrostate.

---

# 46. Por que não usar um Transformer apenas em uma linha de $A(t)$?

Se $K=4$, então:

```math
A_i(t)\in\mathbb R^4.
```

Um Transformer sobre quatro números provavelmente é desnecessário.

PCA/SVD e métricas analíticas são mais transparentes.

Um encoder temporal faz mais sentido sobre:

```math
A_i(t-w),\ldots,A_i(t).
```

Ou sobre um vetor comportamental rico:

```math
x_i(t)
=
[
\text{competence},
\text{confidence},
\text{errors},
\text{routing},
\text{memory composition},
\ldots
].
```

---

# 47. Behavioral phenotype embedding

Podemos definir:

```math
z_i(t)
=
f_\phi
\left(
x_i(t-w:t)
\right)
\in\mathbb R^d.
```

A sociedade vira um conjunto de pontos móveis:

```math
\mathcal Z(t)
=
\{z_1(t),\ldots,z_N(t)\}.
```

Podemos estudar:

- divergência de trajetórias;
- clusters;
- mudança de role;
- retorno após intervenção;
- low-dimensional collective coordinates.

---

# 48. Como treinar o embedding sem criar uma tautologia

Não devemos treinar $f_\phi$ para separar private/shared ou agent IDs e depois usar essa separação como evidência.

Também não devemos otimizar diretamente:

```math
\max_\phi \text{agent separation}.
```

Melhores objetivos:

### Autoencoding

```math
z_i=f_\phi(x_i),
```

```math
\hat x_i=g_\psi(z_i),
```

com:

```math
\mathcal L
=
\|x_i-\hat x_i\|^2.
```

### Predictive representation

```math
z_i(t)=f_\phi(x_i(t-w:t)),
```

```math
\hat A_i(t+\Delta)=g_\psi(z_i(t)).
```

Treinar:

```math
\mathcal L
=
\|A_i(t+\Delta)-\hat A_i(t+\Delta)\|^2.
```

Nesse caso, $z_i$ representa informação dinamicamente relevante para o futuro.

---

# 49. Um critério forte para um macrostate aprendido

Queremos perguntar se:

```math
P(
B_i(t+\Delta)
\mid
\text{história inteira}
)
```

pode ser aproximado por:

```math
P(
B_i(t+\Delta)
\mid
z_i(t)
).
```

Se um $z_i(t)$ de baixa dimensão retém boa capacidade preditiva, ele se comporta como uma variável macroscópica/coarse-grained state.

---

# 50. Individual phenotype versus social role

Uma role pode ser relacional.

### Individual phenotype

```math
z_i^{\mathrm{ind}}(t)
=
f_\phi(x_i(t)).
```

### Social role

```math
z_i^{\mathrm{soc}}(t)
=
g_\psi
\left(
x_i(t),
\{x_j(t)\}_{j\neq i}
\right).
```

Para o segundo caso, arquiteturas permutation-equivariant são mais naturais:

- Deep Sets;
- Set Transformer;
- Graph Neural Network;
- attention sem positional identity arbitrária.

Isso permite testar:

> role é uma propriedade individual ou uma relação com a sociedade?

---

# 51. Intervenções causais futuras

Se roles aparecerem de maneira robusta, podemos testar causalidade diretamente.

## 51.1 Memory swap

```math
M_i\leftrightarrow M_j.
```

Pergunta:

> o papel acompanha a memória?

## 51.2 Memory erase

```math
M_i\to\varnothing.
```

Pergunta:

> o papel desaparece quando apagamos a história individual?

## 51.3 Clone / transplant

```math
M_i\to M_j.
```

Pergunta:

> expertise pode ser transplantada?

## 51.4 Ablation

Remover um agente especializado.

Pergunta:

> a função desaparece ou outro indivíduo preenche o niche?

## 51.5 Naive replacement

Substituir o especialista por uma nova cópia com memória vazia.

Pergunta:

> a estrutura coletiva treina o novo indivíduo para preencher uma posição funcional?

## 51.6 Reintroduction e hysteresis

```math
S_{\mathrm{antes}}
\to
S_{\mathrm{perturbado}}
\to
S_{\mathrm{restaurado}}.
```

Se o estado final depender do caminho:

```math
z_\uparrow(\lambda)\neq z_\downarrow(\lambda),
```

temos path dependence/hysteresis-like behavior.

---

# 52. Regeneration

Depois de ablation, possíveis perguntas:

- performance coletiva se recupera?
- uma competência perdida reaparece?
- um novo agente assume o niche?
- quanto tempo leva?
- a identidade do ocupante muda?
- a estrutura é resiliente sem o indivíduo original?

Isso separa:

```math
\text{role stability}
```

de:

```math
\text{occupant stability}.
```

---

# 53. O piloto atual

O primeiro matched-ish comparison relevante usou:

```text
model: DeepSeek V4 Flash
agents: 4
rounds: 20
probes: 40
router: argmax confidence
epsilon: 0
memory: recent_k = 8
seed: 1
```

Runs:

```text
PRIVATE
private-seed1-20260806T231032Z-ff928a0b

SHARED
shared-seed1-20260807T002355Z-557768c8
```

---

# 54. Resultado exploratório principal

| Condição | HSE norm $t=0$ | HSE norm $t=20$ | $\Delta$HSE |
|---|---:|---:|---:|
| Private | 0.529 | 0.756 | +0.228 |
| Shared | 0.441 | 0.359 | -0.082 |

Outras métricas finais:

| Métrica | Private | Shared |
|---|---:|---:|
| HSE norm | 0.756 | 0.359 |
| task-agent MI norm | 0.121 | 0.277 |
| utilization entropy norm | 0.374 | 0.985 |
| best individual | 0.400 | 0.300 |
| oracle society | 0.650 | 0.475 |
| oracle gain | 0.250 | 0.175 |

Interpretação:

> o private apresentou maior diferenciação comportamental nessa seed, mas não uma divisão de trabalho limpa.

---

# 55. O resultado que impede uma narrativa simplista

No private:

```text
agent_0:  1 seleção
agent_1: 17 seleções
agent_2:  2 seleções
agent_3:  0 seleções
```

Logo:

```math
P(R=\mathrm{agent}_1)=0.85.
```

Isso é winner-take-most.

Ao mesmo tempo, a competence matrix final incluía:

```math
A_{\mathrm{agent_1,BETA}}=1.0.
```

Então apareceu uma competência localizada forte, mas o mesmo agente também recebia tarefas de domínios em que era ruim.

Conclusão:

```math
\boxed{
\text{behavioral differentiation}
\neq
\text{task-structured useful specialization}
}
```

---

# 56. Por que esse resultado ainda é interessante

A surpresa não deve virar automaticamente uma nova tese de “allocation collapse”.

Ela serve principalmente como cautela metodológica:

> HSE crescendo não é suficiente para dizer que especialização emergiu.

O resultado atual sugere que devemos medir em camadas:

```text
diversity
   ↓
task structure
   ↓
competence structure
   ↓
alignment
   ↓
complementarity
   ↓
actual team utility
```

---

# 57. Caveats do piloto

O resultado atual é exploratório porque:

- uma única paired seed;
- 20 rounds;
- apenas checkpoints inicial/final;
- MI com amostra pequena;
- stochastic decoding;
- runtime health desigual;
- algumas logical completions ausentes.

A auditoria posterior mostrou que os commits private/shared diferiam apenas em mudanças não científicas, mas a saúde técnica dos artifacts não é suficiente para chamá-los de clean replication evidence.

---

# 58. Estado atual da infraestrutura

Branch de desenvolvimento:

```text
research/developmental-dynamics
```

A infraestrutura preparada inclui:

- checkpoints regulares;
- online observables;
- multi-seed planning;
- aggregation;
- permutation-invariant analysis;
- MI permutation diagnostics;
- probabilistic feedback locality;
- memory interventions;
- population-state scaffolding;
- initial perturbations;
- recovery metrics;
- minimal non-LLM model.

A auditoria reportou:

```text
77 tests: OK
Python compile: OK
```

O baseline private/shared foi considerado semanticamente preservado.

---

# 59. Batch de replicação preparado

O desenho inicialmente preparado é:

```math
\text{seeds}=\{1,2,3,4,5\},
```

```math
\text{conditions}=\{\mathrm{private},\mathrm{shared}\},
```

```math
T=20,
```

checkpoints:

```math
\{0,10,20\}.
```

Isso corresponde a:

- 10 runs;
- 560 nominal completions/run;
- 5600 nominal completions no total.

Por causa dos problemas de runtime do shared via API/OMP, existe uma razão forte para migrar a infraestrutura principal para inferência local antes de escalar.

---

# 60. Inferência local como direção preferida

O grupo dispõe de duas máquinas descritas como “GTX/DGX Spark”.

Antes de planejar hardware, confirmar o nome/modelo exato.

Se forem NVIDIA DGX Spark ou máquinas equivalentes capazes de servir um open-weight LLM local, a vantagem científica é grande:

- eliminar provider/API variability;
- controlar versão do modelo;
- controlar sampling parameters;
- usar explicit sampling seeds;
- batching;
- rodar dezenas/centenas de seeds;
- evitar timeouts e stream-framing externos;
- registrar infraestrutura exatamente.

A arquitetura desejada é:

```text
Experiment Controller
       |
       +------> local inference server
                  |
                  +--> agent 0 request
                  +--> agent 1 request
                  +--> agent 2 request
                  +--> agent 3 request
```

Não é necessário carregar quatro cópias dos pesos.

Os agentes diferem pelo estado/memória enviado na request.

---

# 61. Sampling seeds e pairing

Uma grande vantagem do backend local é usar seeds por logical call.

Por exemplo:

```math
\xi_{s,t,i}=h(s,t,i),
```

onde:

- $s$ = seed da sociedade;
- $t$ = round/probe;
- $i$ = agente.

Private e shared podem reutilizar a mesma tabela de $\xi$.

Assim:

- a stochasticity entre agentes continua existindo;
- o ruído exógeno pode ser pareado entre condições.

Não usar a mesma sampling seed para todos os agentes se isso os tornar artificialmente idênticos.

---

# 62. Modelo local: critério científico

O modelo deve estar num regime intermediário.

Se for fraco demais:

```math
\text{experience}\not\to\text{learning}.
```

Se for forte demais:

```math
\text{hidden rule}
```

é inferida imediatamente e a memória deixa de importar.

Queremos algo como:

```text
sem experiência       → desempenho baixo/moderado
alguma experiência    → melhora
mais experiência      → regra aprendível
```

A seleção do modelo deve ser feita por calibration pré-registrada de floor/ceiling, e não por escolher o modelo que “produz o fenômeno desejado”.

Para a primeira etapa, um modelo dense open-weight é conceitualmente mais limpo que um MoE, embora MoE possa ser uma excelente robustness replication posterior.

---

# 63. Perguntas que o orientador provavelmente fará

A seguir, perguntas críticas e respostas que devemos estar preparados para dar.

## Q1. “O que exatamente você chama de estrutura funcional?”

Não é simplesmente HSE alta.

Eu separaria:

1. diferenciação: $B_i$ e $A_i$ divergem;
2. task dependence: $I(C;R)>0$;
3. competence structure: agents têm profiles distintos em $A$;
4. alignment: tarefas vão para agentes acima da média naquele domínio;
5. persistence: roles sobrevivem no tempo e a perturbações;
6. utility: a sociedade roteada ganha performance ou cobertura em held-out tasks.

A definição forte seria uma estrutura task-dependent, persistente e útil.

## Q2. “No final você vai avaliar numa tarefa?”

Sim.

O primeiro downstream evaluation é o próprio hidden-world environment em exemplos held-out.

Mediremos:

```math
A_{\mathrm{team}}
=
P(\text{selected answer is correct})
```

e compararemos com melhor single agent, random routing, shared control e oracle.

Depois, para aumentar external validity, devemos ter uma segunda task family ou benchmark procedural.

## Q3. “Você vai botar eles para colaborar?”

Não é necessário para a primeira pergunta.

O paper de origem trata routing como allocation: uma query é atribuída a um ator.

Nosso primeiro fenômeno é especialização/divisão de trabalho mediada por routing.

Colaboração deliberativa adicionaria communication e consensus como confounds.

Depois podemos criar composite tasks que exigem múltiplos niches e testar se a estrutura emergida ajuda numa colaboração real.

## Q4. “Então por que chamar isso de multi-agent se eles não conversam?”

Porque existe uma população de atores adaptativos acoplados por uma política de alocação e por consequências compartilhadas/privadas.

Eles não precisam conversar diretamente para existir interação indireta.

O estado de um agente altera routing; routing altera quem recebe experiência; isso altera as oportunidades futuras dos outros.

Se quisermos ser mais precisos, podemos dizer **adaptive routed LM society**.

## Q5. “O paper original mostra que HSE maior melhora performance?”

Não.

O paper trata HSE/robustness como propriedades estruturais adicionais.

Ele encontra casos em que specialist societies aumentam clean accuracy de KNN, mas robustness piora.

No appendix, selecionar apenas por HSE gera maior diversidade e menor task accuracy que selecionar conjuntamente por HSE + accuracy.

Portanto:

```math
\mathrm{HSE}\uparrow
\not\Rightarrow
\mathrm{performance}\uparrow.
```

## Q6. “Então qual é a utilidade de HSE?”

HSE responde:

> existe um espaço comportamental suficientemente diferenciado para routing não ser trivial?

É uma métrica de estrutura da população.

Ela não mede qualidade do router, task utility, causalidade ou especialização útil.

## Q7. “Por que não usar só a competence matrix $A$?”

$A$ é extremamente importante e deve ser primária no nosso projeto.

HSE é útil porque mantém a ponte direta com o paper, mede diferenças item-level e é multiescala.

Não precisamos escolher uma única métrica.

## Q8. “Eles realmente aprendem se os pesos não mudam?”

O aprendizado é stateful/in-context, não parametric.

O estado relevante é:

```math
M_i(t).
```

O effective agent é:

```math
r_i(t)
=
r_\theta(\cdot\mid M_i(t)).
```

Se quisermos reservar “learning” para atualização de parâmetros, podemos chamar isso de adaptation ou acquired competence through persistent context.

## Q9. “Isso não é só prompt engineering?”

A memória entra no prompt, mas a diferença de contextos não é manualmente projetada por agente.

Todos começam com o mesmo prompt.

A diferença é endógena, resultado da história de assignment.

## Q10. “Os agentes são realmente idênticos?”

Não em cada sample.

Eles são exchangeable / identically configured.

Por stochasticity, $Y_i\neq Y_j$ pode acontecer no primeiro round.

A simetria é de distribuição.

## Q11. “Se HSE já nasce alta por ruído, como você diferencia emergência de stochasticity?”

Por:

- baseline $t=0$;
- $\Delta$HSE;
- shared control;
- muitas paired seeds;
- persistence;
- competence structure;
- task–agent alignment;
- sampling-seed control local.

Randomness gera diversidade quase de graça. O fenômeno interessante é diferença organizada, útil e persistente.

## Q12. “Por que private versus shared?”

Porque é uma manipulação mínima da localidade da informação.

Shared tende a preservar simetria de estado; private permite path dependence.

Não estamos postulando que private seja uma condição necessária ou suficiente geral para especialização.

## Q13. “O confidence router não cria artificialmente rich-get-richer?”

Pode criar.

Isso é simultaneamente um mecanismo candidato e um possível artifact específico do router.

Por isso depois devemos comparar confidence greedy, softmax routing, random allocation, exploration e controles balanceados.

## Q14. “Confidence de LLM é calibrada?”

Não assumimos que seja.

Confidence é uma variável comportamental usada pelo mecanismo de routing.

Calibration pode ser medida separadamente.

## Q15. “O mundo ALPHA/BETA está explicitamente escrito? Isso não entrega a task type?”

O label é semanticamente vazio, mas fornece uma identidade estável para a família de tarefas.

Isso é deliberado no experimento atual: queremos permitir que um agente aprenda regras específicas de um niche sem conhecer sua fórmula.

Uma extensão forte é remover os labels e tornar o world latent.

## Q16. “Essas funções mod 7 não são simples demais?”

São simples propositalmente.

Vantagens:

- ground truth exato;
- complexidade controlada;
- tarefas procedurais infinitas;
- baixo efeito de pretraining;
- controle sobre dificuldade.

Mas o toy environment não pode ser a única evidência de generalidade de um paper grande.

## Q17. “E se o modelo simplesmente deduzir a fórmula em uma observação?”

Fazemos calibration para evitar ceiling.

Podemos aumentar espaço de regras, ambiguity, compositionality ou exigir mais experiências.

## Q18. “O que falsificaria a hipótese?”

Exemplos:

- private e shared produzem as mesmas trajetórias em muitas seeds;
- toda HSE adicional desaparece ao controlar sampling;
- competence matrix não ganha estrutura;
- roles não persistem;
- assignment não se alinha à competência;
- nenhum efeito aparece acima do stochastic baseline.

## Q19. “Por que chamar de symmetry breaking?”

Porque as regras são permutation-symmetric nos labels e o estado inicial é exchangeable, mas trajetórias individuais podem terminar assimétricas.

Com $N=4$, finite-system trajectory-level symmetry breaking é mais defensável que afirmar uma phase transition.

## Q20. “Como provar que nenhum label é privilegiado pelo código?”

Com:

- IDs fora do prompt;
- tie-breaking randomizado/seedado;
- invariância a iteration order;
- RNGs separados;
- permutation-invariant analysis;
- distribuição dos winners por label em muitas seeds.

Esperamos:

```math
P(\text{label }i\text{ ocupa determinada função})
\approx
\frac1N.
```

## Q21. “Qual é a unidade estatística?”

A sociedade/run, não cada model completion.

A comparação principal é paired por experimental seed:

```math
D_s(t)
=
\Delta HSE_{\mathrm{private},s}(t)
-
\Delta HSE_{\mathrm{shared},s}(t).
```

## Q22. “MI não vai ser super enviesada com poucos rounds?”

Sim.

Por isso o plug-in MI é diagnóstico, não prova.

Usamos permutation null e precisamos aumentar $T$.

## Q23. “HSE depende demais de cosine + single linkage?”

Pode depender.

O paper verifica múltiplas distâncias/linkages e encontra padrão qualitativo robusto no seu contexto.

No nosso trabalho, devemos fazer sensitivity analysis e não basear a conclusão inteira em HSE.

## Q24. “Single linkage não sofre chaining?”

Sim.

Essa é uma limitação conhecida.

O paper compara alternativas no appendix.

Complete/average linkage são robustness checks naturais.

## Q25. “O evaluation set define a diversidade. E se ele for ruim?”

Essa é uma limitação reconhecida pelo paper.

Precisamos de fixed held-out probes, múltiplos probe sets, worlds balanceados e procedural resampling.

HSE não é uma propriedade absoluta do agente; é relativa ao evaluation set.

## Q26. “Oracle gain não é uma fantasia, já que o oracle não existe?”

Ele não mede performance implementável.

Ele mede headroom de complementaridade.

Depois perguntamos quanto desse headroom o router captura com $A_{\mathrm{team}}$ e $\eta_{\mathrm{route}}$.

## Q27. “Como distinguir um especialista real de um agente simplesmente globalmente melhor?”

Um global winner melhora vários niches simultaneamente.

Especialização implica heterogeneidade relativa entre dimensões.

Ferramentas:

- matriz $A$;
- centralização $X$;
- $\Phi$;
- espectro/participation ratio;
- matching.

## Q28. “O que seria uma evidência particularmente convincente?”

Uma combinação como:

1. $\Delta$HSE private > shared em muitas seeds;
2. $\Phi$ aumenta;
3. competence matrices ganham estrutura após permutation alignment;
4. $I(C;R)$ aumenta acima do null;
5. $\eta_{\mathrm{route}}>0$;
6. $A_{\mathrm{team}}$ supera baselines;
7. roles persistem;
8. labels ocupantes variam entre seeds;
9. memory swap move a role;
10. ablation gera replacement/regeneration.

## Q29. “Por que memory swap é tão importante?”

Porque permite uma intervenção causal.

Se depois de:

```math
M_A\leftrightarrow M_B
```

as competências/roles também trocam, temos evidência de que a identidade funcional está carregada pela experiência individual.

Se não trocam, a role pode depender do contexto coletivo.

## Q30. “Por que ablation/regeneration?”

Porque diferencia especialista como indivíduo de niche como propriedade da organização.

Se removemos o ocupante e outro assume a função, existe estrutura funcional mais abstrata que o indivíduo original.

## Q31. “Isso já não existe em papers de self-organizing LLM agents?”

Já existem trabalhos recentes observando roles espontâneas/self-organization em populações de LLM agents.

Então a novelty não pode ser simplesmente “LLMs criam roles sem prompt”.

A contribuição distintiva precisa ser algo como:

- homogeneous initialization rigorosa;
- dinâmica quantitativa $B(t)$;
- symmetry/exchangeability analysis;
- causal interventions;
- minimal mathematical model;
- regime characterization;
- link explícito entre diversity, competence, routing e utility.

## Q32. “Isso é só MoE em nível de prompt?”

Existe uma analogia com mixture-of-experts/gating.

Mas aqui:

- agentes têm persistent natural-language state;
- competência pode ser adquirida via experience;
- atores começam com os mesmos pesos;
- estado pode ser transplantado/ablated;
- queremos estudar dynamics, não apenas treinar um gate.

## Q33. “Se você usar um embedding aprendido, não vai fabricar a separação?”

Esse risco existe.

Por isso HSE/$A$/$\Phi$ continuam primary, o embedding fica do lado do observador e deve ser treinado com objetivos predictive/self-supervised, não labels da conclusão.

## Q34. “Por que usar Transformer no embedding?”

Só faz sentido se a entrada for temporal/rica.

Um Transformer sobre $A_i(t)\in\mathbb R^4$ é exagero.

Para a sociedade inteira, Set Transformer/GNN é mais natural por permutation equivariance.

## Q35. “Qual seria a matemática publicável?”

A oportunidade é combinar:

1. processo estocástico;
2. permutation symmetry;
3. constrained memory simplex;
4. reinforcement;
5. mean-field;
6. fixed points;
7. linear stability;
8. regime map;
9. predictions testadas em LLMs.

O melhor cenário é:

```text
minimal model
     ↓ predicts
collective regimes
     ↓ tested in
controlled LLM society
```

## Q36. “O que faria isso virar um paper, e não um projeto legal?”

Provavelmente uma combinação de:

- fenômeno robusto em muitas seeds;
- pelo menos dois modelos/famílias;
- definição operacional clara de functional structure;
- causal interventions;
- teoria mínima com previsões não triviais;
- validação fora do toy inicial;
- comparison com baselines;
- relação rigorosa com routing, task allocation e self-organization.

O toy modular sozinho é um laboratório, não o paper inteiro.

---

# 64. O que o paper forte poderia reivindicar

Evitar:

> “Private memory causes specialization.”

Mais forte e defensável seria algo como:

> **We study the developmental dynamics of initially exchangeable language-model societies and identify conditions under which routing-mediated experience generates persistent functional differentiation.**

Se houver resultados de causalidade:

> **We show that emergent roles can be causally manipulated through memory transplantation and can, under some regimes, be regenerated after agent ablation.**

Se houver teoria:

> **A minimal reinforced-allocation model predicts qualitative regimes observed in controlled LLM societies.**

Essas claims dependem dos dados futuros.

---

# 65. Roadmap científico recomendado

## Fase A — replicar o fenômeno básico

Objetivo:

```math
B\to B(t)
```

com muitas seeds.

Manter private vs shared e controlar modelo, tasks, probes e sampling.

Perguntas:

- $\Delta$HSE reproduz?
- $\Phi$ reproduz?
- existe task structure?
- labels permanecem exchangeable no ensemble?

## Fase B — medir functional utility explicitamente

Adicionar formalmente:

```math
A_{\mathrm{team}},
```

```math
U_{\mathrm{route}},
```

```math
U_{\mathrm{rand}},
```

```math
U_{\mathrm{oracle-domain}},
```

```math
\eta_{\mathrm{route}},
```

```math
U_{\mathrm{match}}.
```

## Fase C — localidade da informação como parâmetro

Generalizar:

```math
\lambda\in[0,1].
```

Perguntar se $z_\infty(\lambda)$ muda qualitativamente.

## Fase D — causal interventions

- memory swap;
- erase;
- clone;
- transplant;
- ablation;
- replacement;
- reintroduction.

Pergunta central:

> onde uma role emergente “vive”?

## Fase E — modelo mínimo

Desenvolver a dinâmica em:

```math
(\Delta^{K-1})^N.
```

Estudar symmetric/asymmetric fixed points, stability, reinforcement, capacity constraints e coexistence/fixation.

## Fase F — generalização

Replicar em:

- outro open-weight model;
- outra escala;
- dense vs MoE;
- outra família procedural;
- benchmark externo apropriado.

## Fase G — colaboração real

Somente depois.

Criar composite tasks em que performance ótima exige combinar competências de múltiplos niches.

---

# 66. O que NÃO fazer cedo demais

Evitar transformar o projeto prematuramente em:

- epsilon tuning;
- router optimization;
- HSE maximization;
- “anti-collapse algorithm”;
- huge agent framework;
- dashboard;
- benchmark zoo;
- phase-transition claim;
- learned embedding como única métrica.

O núcleo científico deve permanecer legível.

---

# 67. O que é interessante independentemente do resultado

## Caso A — diferenciação robusta + utilidade

Candidato forte a emergent functional organization.

## Caso B — diferenciação robusta sem utilidade

Resultado importante:

> diversity can emerge without useful specialization.

## Caso C — monopoly dominante

Pode indicar que reinforcement simples tende a fixation, não division of labor.

## Caso D — shared e private iguais

A assimetria informacional do nosso mecanismo não é a causa principal.

## Caso E — enorme variação entre seeds

Pode indicar forte path dependence/multiple metastable outcomes.

## Caso F — nada reproduz

O seed inicial foi uma trajetória atípica ou stochastic artifact.

Todos são cientificamente interpretáveis.

---

# 68. Pitch técnico para o orientador

> O paper original define a diversidade de uma sociedade por meio de um behavioral matrix $B$ e HSE, que integra a Shannon entropy das partições do espaço comportamental ao longo de diferentes resoluções de um clustering hierárquico. Ele também mede routing robustness e deixa explícito que estabilidade do assignment é uma condição necessária, não suficiente, para especialização.
>
> O que eu quero fazer é tornar $B$ dinâmico, $B(t)$. Os agentes começam exchangeable: mesmos pesos, mesmo prompt e memória vazia. A única diferença possível aparece endogenamente através da história de assignment e feedback.
>
> Isso pode ser formalizado como um processo estocástico permutation-equivariant. A pergunta é se o estado simétrico é estável ou se pequenas flutuações são amplificadas pelo feedback entre routing e experiência.
>
> Uma modelagem mínima representa a memória de cada agente como um ponto num simplex de niches. Routing depende da competência associada à composição da memória; quando somente o agente selecionado recebe experiência, aparece reinforcement. Como a memória é finita, existe também competição por capacidade.
>
> Isso gera uma dinâmica não linear num produto de simplexes, em que podemos estudar fixed points, stability, winner-take-all, division-of-labor e outros regimes. Depois podemos testar essas previsões em muitas realizações de sociedades locais de LLMs.
>
> O objetivo não é apenas mostrar que os agentes ficam diferentes. É entender quando a diferença vira estrutura funcional: competência task-dependent, routing alinhado a essa competência, persistência e utilidade coletiva.

---

# 69. Pitch de 60 segundos

> O paper *When is Routing Meaningful?* mede quão diversa é uma sociedade de LLMs já existente usando HSE e pergunta se o routing é estável. Eu quero estudar a pergunta anterior: de onde essa diversidade vem?
>
> Começo com agentes exchangeable — mesmo modelo, mesmo prompt, mesma memória vazia — e deixo o routing criar histórias de experiência diferentes. Em checkpoints, construo $B(t)$ e uma competence matrix $A(t)$.
>
> A parte matemática que me interessa é tratar isso como um processo estocástico com simetria de permutação e estudar a estabilidade do estado simétrico. Um modelo mínimo coloca a memória de cada agente num simplex de nichos; reinforcement aumenta a probabilidade de receber tarefas parecidas, mas capacidade finita produz competição.
>
> Então a pergunta deixa de ser “roles aparecem?” e vira “quais estados coletivos são estáveis, quando a simetria quebra e quando essa quebra produz estrutura funcional útil?”. Depois podemos testar causalidade trocando memórias ou removendo especialistas.

---

# 70. O que é fato, o que é piloto e o que é hipótese

| Tipo | Item |
|---|---|
| Paper original | define behavioral matrix $B$ |
| Paper original | adapta HSE para LM societies |
| Paper original | propõe routing robustness |
| Paper original | não afirma que HSE maior garante performance |
| Paper original | não mede desenvolvimento de specialised competence |
| Paper original | cita homogeneous initialization como direção futura |
| Piloto | private seed 1 teve $\Delta$HSE positivo |
| Piloto | shared seed 1 teve $\Delta$HSE negativo |
| Piloto | private concentrou 17/20 selections em um agente |
| Piloto | apareceu competência local alta em BETA |
| Hipótese | private/shared contrast será reproduzível |
| Proposta matemática | $\Phi(t)$ como order parameter |
| Proposta matemática | memory-simplex mean-field |
| Proposta matemática | $\eta_{\mathrm{route}}$ como alignment/capture efficiency |
| Proposta matemática | $U_{\mathrm{match}}$ como division-of-labor potential |
| Proposta | learned behavioral macrostate $z_i(t)$ |
| Proposta | memory transplant / ablation / regeneration |
| Proposta | regime map e possíveis bifurcações |
| Não estabelecido | phase transition |
| Não estabelecido | emergent specialization geral em LLM societies |
| Não estabelecido | vantagem de performance do private |

---

# 71. Glossário

### Actor

Um modelo/agente disponível para receber uma query.

### Router

Política que escolhe qual ator recebe/resolve uma tarefa.

### Behavioral vector

Vetor de scores de um ator num evaluation set comum.

### Behavioral matrix $B$

Matriz cujas linhas são behavioral vectors.

### HSE

Hierarchic Social Entropy: integral da Shannon entropy das partições obtidas ao variar a resolução de clustering.

### Routing robustness

Estabilidade do assignment sob meaning-preserving perturbations.

### Exchangeability

Ausência de significado intrínseco nos labels dos agentes; trocar labels não muda a distribuição inicial.

### Symmetry breaking

Uso operacional: uma realização inicialmente exchangeable desenvolve assimetria persistente sem role previamente atribuída.

### Competence matrix $A$

```math
A_{ic}=P(\text{correct}\mid i,c).
```

### Utilization entropy

Entropia da distribuição de selection entre agentes.

### Oracle gain

Ganho potencial de uma sociedade se um oracle pudesse escolher o agente correto para cada item.

### Functional structure

Diferenciação organizada por tarefa, competência e alocação, idealmente persistente e útil.

### Niche

Uma classe/família de tarefas que pode sustentar competência especializada.

### Coarse-graining

Mapeamento de um microstate complexo para poucas variáveis macroscópicas relevantes.

---

# 72. Equações essenciais — cheat sheet

Behavioral matrix:

```math
B(t)
=
\begin{bmatrix}
b_1(t)^\top\\
\vdots\\
b_N(t)^\top
\end{bmatrix}.
```

Cosine behavioral distance:

```math
d_{ij}
=
1-
\frac{b_i^\top b_j}
{\|b_i\|\|b_j\|}.
```

Social entropy:

```math
H(h)
=
-\sum_cp_c(h)\log_2p_c(h).
```

HSE:

```math
\mathrm{HSE}
=
\int_0^\infty H(h)\,dh.
```

Competence matrix:

```math
A_{ic}(t)
=
P(\text{correct}\mid i,c,t).
```

Differentiation order parameter:

```math
\Phi(t)
=
\frac1{NK}
\left\|
A(t)-\mathbf1\bar A(t)^\top
\right\|_F^2.
```

Utilization entropy:

```math
H(R)
=
-\sum_iP(R=i)\log_2P(R=i).
```

Task-agent MI:

```math
I(C;R)
=
\sum_{c,r}
p(c,r)
\log_2
\frac{p(c,r)}{p(c)p(r)}.
```

Actual team accuracy:

```math
A_{\mathrm{team}}
=
\frac1T
\sum_t
\mathbf1[
Y_{R_t,t}=Y_t^\star
].
```

Structural routed utility:

```math
U_{\mathrm{route}}
=
\sum_cp(c)
\sum_iP(R=i\mid C=c)A_{ic}.
```

Random-routing baseline:

```math
U_{\mathrm{rand}}
=
\sum_cp(c)\bar A_c.
```

Domain oracle:

```math
U_{\mathrm{oracle-domain}}
=
\sum_cp(c)\max_iA_{ic}.
```

Routing capture efficiency:

```math
\eta_{\mathrm{route}}
=
\frac{
U_{\mathrm{route}}-U_{\mathrm{rand}}
}{
U_{\mathrm{oracle-domain}}-U_{\mathrm{rand}}
}.
```

Best one-to-one role assignment:

```math
U_{\mathrm{match}}
=
\max_{\sigma\in S_N}
\frac1K
\sum_cA_{\sigma(c),c}.
```

Oracle complementarity:

```math
\Delta_{\mathrm{comp}}
=
A_{\mathrm{oracle}}-A_{\mathrm{best}}.
```

Memory simplex:

```math
x_i\in\Delta^{K-1}.
```

Softmax assignment:

```math
p_i(c)
=
\frac{
e^{\beta g(x_{ic})}
}{
\sum_je^{\beta g(x_{jc})}
}.
```

Private mean-field proposal:

```math
\dot x_{ic}
=
\eta
\left[
\rho_cp_i(c)
-
x_{ic}\sum_d\rho_dp_i(d)
\right].
```

Shared mean-field proposal:

```math
\dot x_{ic}
=
\eta(\rho_c-x_{ic}).
```

---

# 73. Referências centrais

## Paper de origem

Huot, F.; Kaisers, M.; Lapata, M. (2026).  
**When is Routing Meaningful? Diversity and Robustness in Language Model Societies.**  
arXiv:2607.09197.

## HSE original

Balch, T. (2000).  
**Hierarchic Social Entropy: An Information Theoretic Measure of Robot Group Diversity.**  
*Autonomous Robots*, 8(3), 209–237.  
DOI: 10.1023/A:1008973424594.

## Division of labor / response threshold

Theraulaz, G.; Bonabeau, E.; Deneubourg, J.-L. (1998).  
**Response Threshold Reinforcement and Division of Labour in Insect Societies.**  
*Proceedings of the Royal Society B*, 265(1393), 327–332.  
DOI: 10.1098/rspb.1998.0299.

Beshers, S. N.; Fewell, J. H. (2001).  
**Models of Division of Labor in Social Insects.**  
*Annual Review of Entomology*, 46, 413–440.  
DOI: 10.1146/annurev.ento.46.1.413.

## Related work recente a revisar com cuidado

Há preprints recentes sobre self-organizing LLM agents e emergent roles. Eles são importantes para o novelty positioning, mas não devem ser usados como evidência de que nossa formulação já foi estudada.

Exemplo a revisar:

- Dochkina, V. (2026), **Drop the Hierarchy and Roles: How Self-Organizing LLM Agents Outperform Designed Structures**, arXiv:2603.28990.

Também há trabalhos recentes de large-scale autonomous agent populations e estudos mostrando que self-organizing LLM teams nem sempre conseguem explorar corretamente seus especialistas. Essa literatura deve entrar numa revisão bibliográfica formal antes de qualquer claim de novelty.

---

# 74. Instruções para uma futura sessão de ChatGPT/Codex

Ao usar este documento como contexto:

1. Trate o paper de Huot et al. como a referência conceitual principal.
2. Preserve a distinção:

```math
\text{diversity}
\neq
\text{specialization}
\neq
\text{useful division of labor}.
```

3. Não diga que o piloto demonstrou emergent specialization.
4. Não transforme o projeto automaticamente em “routing collapse optimization”.
5. O eixo principal é:

```math
B\to B(t).
```

6. A matemática em simplex, $\Phi$, $\eta_{\mathrm{route}}$, $U_{\mathrm{match}}$ e learned embeddings são **propostas de desenvolvimento**, não resultados do paper original.
7. Pergunte sempre:
   - o fenômeno é reproduzível?
   - é permutation-invariant?
   - está acima do stochastic baseline?
   - está alinhado à competência?
   - é persistente?
   - é útil?
8. Antes de sugerir uma phase transition, exigir evidence de regimes, scaling e stability.
9. Se código e este documento divergirem, o commit congelado e os raw artifacts têm prioridade para detalhes experimentais.
10. O próximo avanço científico deve simplificar a inferência causal, não adicionar complexidade por estética.

---

# 75. Síntese final

A história intelectual do projeto é:

```math
\text{routing meaningful}
\to
\text{behavioral diversity}
\to
B
\to
B(t)
\to
\text{dynamics of differentiation}
\to
\text{functional structure}
\to
\text{causal role formation}
\to
\text{theory of adaptive societies}.
```

O paper original fornece uma forma de medir uma sociedade.

Nosso projeto tenta estudar **a gênese dessa sociedade**.

A pergunta mais importante não é:

> “os agentes ficaram diferentes?”

É:

```math
\boxed{
\text{quando diferenças microscópicas se tornam organização funcional macroscópica?}
}
```

E a pergunta downstream que impede o projeto de virar apenas uma história de HSE é:

```math
\boxed{
\text{essa organização permite que a sociedade aloque e use competência melhor
do que baselines sem estrutura?}
}
```

Se conseguirmos conectar:

- medidas comportamentais;
- utilidade real;
- causal interventions;
- permutation symmetry;
- modelo mínimo com previsões;

o projeto deixa de ser apenas um experimento curioso com LLMs e passa a ser uma investigação quantitativa sobre **desenvolvimento de organização funcional em sistemas adaptativos de agentes**.

---

# ADDENDUM — Estado Atual da Pesquisa e da Campanha

> **Status:** atualização pós-conversão da campanha para execução staged e durante a execução real do Gate 1.  
> **Importante:** resultados listados como “live snapshot” não substituem o relatório final do Gate 1.

---

# 76. O que mudou desde a primeira versão deste documento

O documento anterior estava **conceitualmente forte**, mas deixou de estar operacionalmente completo depois de três mudanças importantes.

## 76.1 A pergunta científica ficou maior

A ideia inicial era:

> “Agentes inicialmente iguais podem se especializar?”

A formulação mais forte passou a ser:

```math
\boxed{
\text{Como sociedades de LLMs inicialmente exchangeable desenvolvem organização funcional?}
}
```

E a sequência agora é:

```text
EMERGENCE
Como a diferenciação aparece?
        ↓
ROLE FORMATION
Quando a diferença vira uma função persistente?
        ↓
CAUSALITY
Onde a role vive?
        ↓
TRANSPLANTATION
Ela acompanha a memória/estado?
        ↓
REGENERATION
A sociedade recompõe uma função perdida?
```

O título “paper grande” que melhor captura isso continua sendo:

> **The Development of Language Model Societies: Symmetry Breaking, Role Formation, and Regeneration from Homogeneous Agents**

Alternativa:

> **From Homogeneity to Roles: Development, Transplantation and Regeneration in LLM Societies**

Uma versão conservadora, caso os resultados não suportem regeneration:

> **Developmental Dynamics of Functional Differentiation in Initially Exchangeable Language-Model Societies**

---

# 77. A frase central que conecta tudo

O paper de origem mede uma sociedade já dada.

Nosso projeto estuda a formação dessa sociedade.

Em símbolos:

```math
\boxed{
B \longrightarrow B(t)
}
```

Em palavras:

> **The source paper measures the structure of a society; we study the genesis of that structure.**

E, mecanisticamente:

> **Routing may not merely exploit actor diversity; through asymmetric experience, it may help generate the diversity it later exploits.**

---

# 78. Mapa de objetos matemáticos: não confundir as camadas

A forma mais segura de entender o projeto é separar os objetos.

```text
MICROSTATE
M_i(t), historical responses, feedback, sampling noise
        │
        ▼
BEHAVIOR
b_i(t), B(t)
        │
        ├──────────────► HSE(t)
        │                 behavioral differentiation
        │
        ▼
COMPETENCE
A_i(t)
        │
        ├──────────────► Phi(t)
        │                 amount of competence differentiation
        │
        └──────────────► d_eff(t)
                          dimensionality of differentiation

TASK ALLOCATION
C_t ───────────────► R_t
        │             │
        ├─────────────┴────► I(C;R)
        │                    task dependence
        │
        └──────────────────► H(R)
                             utilization

ALIGNMENT
A(t) + P(R|C)
        │
        └──────────────► eta_route
                          does routing exploit competence?

COLLECTIVE VALUE
individual + oracle + routed system
        │
        ├──────────────► oracle gain
        ├──────────────► U_match
        └──────────────► A_team
```

A regra epistemológica é:

```math
\boxed{
\text{uma métrica responde uma pergunta; nenhuma responde todas.}
}
```

---

# 79. A hierarquia das claims

## Nível A — diferença comportamental

```math
\mathrm{HSE}(t)\text{ cresce}
```

Claim permitida:

> os agentes ficaram mais diferentes em behavioral space.

Claim proibida:

> eles se especializaram.

---

## Nível B — diferença de competência

```math
\Phi(t)\text{ cresce}
```

Claim permitida:

> os agentes desenvolveram competence profiles mais diferentes.

Ainda não prova niches úteis.

---

## Nível C — task-dependent allocation

```math
I(C;R)>\text{null}
```

Claim permitida:

> task type carrega informação sobre quem é selecionado.

Ainda não prova que o agente selecionado é o certo.

---

## Nível D — functional alignment

```math
\eta_{\mathrm{route}}>0
```

Claim permitida:

> o routing explora parte da competence structure disponível.

---

## Nível E — complementarity

```math
\Delta_{\mathrm{comp}}>0
```

Claim permitida:

> a sociedade contém cobertura complementar que nenhum agente possui sozinho.

Ainda não prova que o sistema consegue capturá-la.

---

## Nível F — useful collective organization

Precisamos de performance real/held-out:

```math
A_{\mathrm{team,heldout}}
```

comparada a baselines adequados.

---

## Nível G — causal role formation

Intervenções como:

```math
M_A\leftrightarrow M_B
```

ou ablation/replacement.

Aqui começamos a falar sobre **onde** a role reside.

---

# 80. $\Phi(t)$ em detalhe

Defina a matriz de competência:

```math
A(t)\in[0,1]^{N\times K},
```

com:

```math
A_{ic}(t)
=
P(\text{correct}\mid i,c,t).
```

Média da sociedade no niche $c$:

```math
\bar A_c(t)
=
\frac1N\sum_i A_{ic}(t).
```

Centralização:

```math
X_{ic}(t)
=
A_{ic}(t)-\bar A_c(t).
```

Parâmetro de diferenciação:

```math
\boxed{
\Phi(t)
=
\frac{1}{NK}\|X(t)\|_F^2
}
```

ou:

```math
\boxed{
\Phi(t)
=
\frac1K\sum_c \mathrm{Var}_i[A_{ic}(t)]
}
```

usando population variance.

### Leitura pedestre

Pegue cada mundo separadamente.

Pergunte:

> “Os quatro agentes têm a mesma accuracy aqui?”

Calcule a variância.

Repita para todos os mundos e faça a média.

Se todo mundo é igualmente competente:

```math
\Phi=0.
```

Se competências divergem:

```math
\Phi>0.
```

### O que $\Phi$ não sabe

Considere:

```math
A=
\begin{bmatrix}
.9&.9&.9&.9\\
.2&.2&.2&.2\\
.2&.2&.2&.2\\
.2&.2&.2&.2
\end{bmatrix}.
```

$\Phi$ é alta, mas isso é um global winner.

Compare:

```math
A=
\begin{bmatrix}
.9&.2&.2&.2\\
.2&.9&.2&.2\\
.2&.2&.9&.2\\
.2&.2&.2&.9
\end{bmatrix}.
```

Também há grande $\Phi$, mas agora existe niche structure.

Por isso entra o espectro.

---

# 81. $d_{\mathrm{eff}}$: dimensão efetiva da diferenciação

Com:

```math
X=A-\mathbf 1\bar A^\top,
```

construa:

```math
Q=\frac1KXX^\top.
```

Seus autovalores são:

```math
\lambda_1,\ldots,\lambda_N\ge0.
```

Participation ratio:

```math
\boxed{
d_{\mathrm{eff}}
=
\frac{\left(\sum_j\lambda_j\right)^2}
{\sum_j\lambda_j^2}
}
```

quando $X\neq0$.

## 81.1 Caso rank-1

Se:

```math
\lambda_1>0,
\qquad
\lambda_{j>1}=0,
```

então:

```math
d_{\mathrm{eff}}=1.
```

Leitura:

> quase toda diferenciação pode ser descrita por um único eixo.

Exemplo típico candidato:

> um agente globalmente melhor que os outros.

## 81.2 $m$ modos igualmente fortes

Se:

```math
\lambda_1=\cdots=\lambda_m=\lambda,
```

então:

```math
d_{\mathrm{eff}}=m.
```

Leitura:

> há aproximadamente $m$ direções independentes de diferenciação.

### Pareamento conceitual

```math
\boxed{
\Phi=\text{quanto os agentes diferem em competência}
}
```

```math
\boxed{
d_{\mathrm{eff}}=\text{quantas direções efetivas compõem essa diferença}
}
```

---

# 82. Utilization entropy em detalhe

Se:

```math
p_i=P(R=i),
```

então:

```math
H(R)=-\sum_i p_i\log_2p_i.
```

Normalizada:

```math
H_{\mathrm{util}}
=
\frac{H(R)}{\log_2N}.
```

Podemos traduzir para número efetivo de agentes:

```math
\boxed{
N_{\mathrm{eff}}=2^{H(R)}=N^{H_{\mathrm{util}}}
}
```

Para $N=4$:

- $H_{\mathrm{util}}=1$ significa $N_{\mathrm{eff}}=4$;
- $H_{\mathrm{util}}=0.5$ significa $N_{\mathrm{eff}}=2$;
- $H_{\mathrm{util}}=0$ significa $N_{\mathrm{eff}}=1$.

Isso torna o número muito mais intuitivo.

---

# 83. MI e seu null: a interpretação correta

Temos:

```math
I(C;R)
=
\sum_{c,r}p(c,r)
\log_2\frac{p(c,r)}{p(c)p(r)}.
```

Com apenas 20 rounds, a tabela é pequena.

Mesmo routing aleatório pode produzir:

```math
\hat I(C;R)>0
```

por finite-sample noise.

Então a pergunta não é:

> “MI é diferente de zero?”

A pergunta é:

> “MI observado é maior do que esperaríamos ao embaralhar assignment sem relação com task?”

Permutação:

```math
I^{(1)}_{\mathrm{perm}},\ldots,I^{(B)}_{\mathrm{perm}}.
```

E:

```math
I_{\mathrm{excess}}
=
I_{\mathrm{obs}}
-
\mathbb E[I_{\mathrm{perm}}].
```

Gate 1 deve interpretar principalmente isso, não plugin MI isolada.

---

# 84. Alignment: uma peça que faltava na primeira história

Mesmo que:

```math
I(C;R)\gg0,
```

o router pode estar sistematicamente escolhendo o agente errado.

Por isso:

```math
U_{\mathrm{route}}
=
\sum_cp(c)\sum_iP(R=i\mid C=c)A_{ic}.
```

Baseline aleatório:

```math
U_{\mathrm{rand}}
=
\sum_cp(c)\bar A_c.
```

Oracle por domínio:

```math
U_{\mathrm{oracle-domain}}
=
\sum_cp(c)\max_iA_{ic}.
```

Eficiência de captura:

```math
\boxed{
\eta_{\mathrm{route}}
=
\frac{U_{\mathrm{route}}-U_{\mathrm{rand}}}
{U_{\mathrm{oracle-domain}}-U_{\mathrm{rand}}}
}
```

### Interpretação

```text
eta ≈ 1
router captures most available competence structure

eta ≈ 0
router is no better than task-agnostic allocation

eta < 0
router systematically misuses available competence
```

Essa métrica é especialmente importante porque literatura recente de LLM teams mostra que **identificar expertise e aproveitá-la são problemas diferentes**.

---

# 85. Matching: existe divisão de trabalho potencial?

Para $N=K$:

```math
U_{\mathrm{match}}
=
\max_{\sigma\in S_N}
\frac1K\sum_cA_{\sigma(c),c}.
```

É um assignment problem.

Compare:

```math
U_{\mathrm{single}}
=
\max_i\frac1K\sum_cA_{ic}.
```

Então:

```math
\Delta_{\mathrm{match}}
=
U_{\mathrm{match}}-U_{\mathrm{single}}.
```

Pergunta:

> Se pudéssemos designar um agente diferente a cada niche, existiria uma organização melhor do que usar o melhor generalista em tudo?

Isso mede **potencial**, não routing real.

---

# 86. A ideia de “role” precisa ser relacional

Ser especialista em ALPHA não é apenas:

```math
A_{i,\mathrm{ALPHA}}\text{ alto}.
```

Pode exigir:

```math
A_{i,\mathrm{ALPHA}}
>
A_{j,\mathrm{ALPHA}}
\quad\forall j\neq i,
```

e talvez uma concentração relativa do próprio agente:

```math
A_{i,\mathrm{ALPHA}}
>
A_{i,c}
\quad\text{para outros }c.
```

Portanto role tem componente:

- individual;
- comparativo;
- social.

Isso motiva no futuro representações set/permutation-aware.

---

# 87. Learned embeddings: atualização do framing

A ideia de embedding continua válida, mas não deve substituir $A$, $\Phi$ ou HSE.

Camadas:

```math
\boxed{
\text{microstate}
\to
\text{interpretable phenotype }A_i(t)
\to
\text{learned macrostate }z_i(t)
}
```

O objetivo mais defensável é predictive:

```math
z_i(t)=f_\phi(x_i(t-w:t)),
```

```math
\hat A_i(t+\Delta)=g_\psi(z_i(t)).
```

Loss:

```math
\mathcal L
=
\|A_i(t+\Delta)-\hat A_i(t+\Delta)\|^2.
```

Assim o embedding é útil se comprime informação que realmente prediz a dinâmica futura.

Não treinar para separar agent IDs/private/shared e depois usar essa separação como “descoberta”.

---

# 88. Coarse-graining: uma leitura de física

Microstate:

```text
full text memory
exact order of experiences
answers
confidence
routing history
feedback
sampling noise
...
```

Macrostate candidato:

```math
z_i(t)\in\mathbb R^d.
```

A pergunta forte:

```math
P(B_i(t+\Delta)\mid\text{full history})
\approx
P(B_i(t+\Delta)\mid z_i(t))?
```

Se sim, $z_i$ é uma variável macroscópica preditiva.

Isso conecta naturalmente a coarse-graining e Information Bottleneck, mas é uma direção futura, não o current Gate 1.

---

# 89. Processo estocástico e simetria

Estado coletivo:

```math
S_t=(M_1(t),\ldots,M_N(t)).
```

Transição:

```math
S_{t+1}
\sim
K_\lambda(\cdot\mid S_t,Z_t,\xi_t).
```

$\xi_t$ agrega stochastic decoding/tie randomness etc.

Se $P_\sigma$ permuta labels:

```math
K(P_\sigma S'\mid P_\sigma S)
=
K(S'\mid S)
```

é a propriedade desejada de permutation equivariance.

Uma realização pode quebrar simetria:

```math
S_t\neq P_\sigma S_t,
```

mesmo se a distribuição ensemble continuar simétrica.

Isso é a forma matematicamente mais interessante de falar de spontaneous differentiation.

---

# 90. Dentro da run vs ensemble

Queremos simultaneamente:

```math
\boxed{
\text{within-run asymmetry}
}
```

e:

```math
\boxed{
\text{ensemble label symmetry}
}
```

Exemplo:

```text
seed 1: ALPHA role → agent 2
seed 2: ALPHA role → agent 0
seed 3: ALPHA role → agent 3
seed 4: ALPHA role → agent 1
```

Cada sociedade é assimétrica.

Nenhum label é especial na distribuição de runs.

Se agent 0 sistematicamente vence, suspeitar de implementação antes de celebrar emergence.

---

# 91. Memória em simplex: explicação ainda mais pedestre

Imagine que cada agente só consegue carregar oito cartões de experiência.

Cada cartão tem uma cor:

```text
ALPHA = vermelho
BETA = azul
GAMMA = verde
DELTA = amarelo
```

Se a memória de agent 0 tem:

```text
█████ ALPHA
██    BETA
█     GAMMA
0     DELTA
```

podemos representar a composição por:

```math
x_0=(5/8,2/8,1/8,0).
```

Como as frações somam 1:

```math
x_0\in\Delta^3.
```

Se entram mais cartões ALPHA e a memória é finita, algum cartão antigo precisa sair.

Esse trade-off é o motivo pelo qual finite memory pode criar niche pressure em vez de aprendizado ilimitado de tudo.

---

# 92. Mean-field em linguagem intuitiva

Private:

> a taxa de ALPHA na memória de um agente cresce com a frequência de ALPHA **vezes a chance desse agente receber ALPHA**, mas é compensada pela expulsão/normalização causada por capacidade finita.

Daí:

```math
\dot x_{ic}
=
\eta\left[
\rho_cp_i(c)
-
x_{ic}\sum_d\rho_dp_i(d)
\right].
```

Shared:

> todo mundo vê a mesma distribuição global de tarefas.

Então:

```math
\dot x_{ic}
=
\eta(\rho_c-x_{ic}),
```

com fixed point:

```math
x_{ic}^*=\rho_c
```

para todos os agentes.

O contraste matemático é muito limpo:

```text
shared
same forcing → same attractor

private
state-dependent assignment → nonlinear feedback
```

---

# 93. O toy de estabilidade e sua limitação

Perto do estado simétrico, com softmax:

```math
p_i\approx\frac1N+\frac{\beta}{N}\delta_i.
```

Uma dinâmica reinforcement simples pode gerar:

```math
\delta_i(t+1)
\approx
\left(1+\frac{\eta\lambda\beta}{N}\right)\delta_i(t).
```

Se o multiplicador é maior que 1, perturbações crescem.

Mas isso prevê principalmente **amplification**, não divisão de trabalho.

Para obter coexistência de roles, precisamos de trade-offs/niche structure.

Essa distinção é tão importante quanto a derivação.

---

# 94. Conexão com response-threshold reinforcement

Theraulaz, Bonabeau & Deneubourg (1998) propõem que indivíduos possuem thresholds de resposta a tarefas.

Executar a tarefa reduz o threshold correspondente; não executá-la pode elevá-lo.

Isso gera:

```math
\text{task performed}
\to
\text{higher future propensity}
\to
\text{task performed again}.
```

A partir de indivíduos inicialmente similares podem emergir specialists.

Mais importante para nosso “paper grande”: o trabalho discute previsões de **remoção e reintrodução de especialistas**.

Isso faz ablation/regeneration deixar de ser uma ideia decorativa e virar uma ponte direta para uma literatura clássica de division of labor.

---

# 95. Conexão com Mixture of Experts

Jacobs et al. (1991):

```math
p(y\mid x)
=
\sum_r p(r\mid x)p(y\mid x,r).
```

O gate distribui responsabilidade de treinamento.

A responsabilidade ajuda a formar expertise.

Nosso sistema não treina parâmetros do expert, mas existe analogia:

```math
\text{routing}
\to
\text{experience responsibility}
\to
\text{state adaptation}
\to
\text{future routing signal}.
```

O ponto histórico importante:

> especialização endógena por assignment não é uma ideia nova em ML; o espaço novo é como isso se manifesta em sociedades stateful de LLMs com pesos compartilhados e como medir/intervir na dinâmica.

---

# 96. Conexão com reinforced processes

Pólya-like intuition:

```text
color drawn
   ↓
more balls of same color
   ↓
color more likely to be drawn
```

Nosso analogue:

```text
agent selected
   ↓
agent receives experience
   ↓
agent may become more likely to be selected
```

Isso sugere:

- path dependence;
- fixation;
- early-noise amplification;
- multiple possible outcomes.

Mas uma Pólya urn não possui task-specific finite memory da mesma maneira, então a analogia não deve ser confundida com um modelo exato.

---

# 97. Por que self-organizing LLM papers não eliminam nossa novelty

Há trabalhos 2026 relatando self-organizing LLM teams que inventam roles sem roles pré-designadas.

Logo a novelty **não pode** ser:

> “descobrimos que LLMs podem inventar papéis.”

O nosso pacote distintivo é potencialmente:

1. identical weights / rigorous exchangeability;
2. $B(t)$ como objeto longitudinal;
3. permutation symmetry;
4. competence order parameter $\Phi$;
5. spectral dimensionality;
6. separation between competence and allocation;
7. causal memory interventions;
8. ablation/regeneration;
9. minimal dynamical model.

É uma pergunta mais mecanística e matemática.

---

# 98. Por que “Multi-Agent Teams Hold Experts Back” é relevante

Pappu et al. (2026) reportam um problema conceitualmente próximo:

> uma equipe pode possuir expertise e ainda falhar em aproveitar o expert.

Isso reforça nossa decomposição:

```math
\boxed{
\text{expertise exists}
\neq
\text{expertise is used}
}
```

No nosso framework:

- $A$ mede expertise;
- oracle gain/matching medem potential;
- $\eta_{\mathrm{route}}$ mede exploitation;
- team accuracy mede realized performance.

---

# 99. Estado operacional atual: backend

A campanha staged atual usa:

```text
DeepSeek Direct
```

com credencial pelo macOS Keychain.

Não confundir com os experimentos antigos que usavam OMP RPC.

No preflight staged:

- OMP não foi utilizado;
- Bitwarden não foi acessado;
- secrets não foram impressos;
- chamadas reais eram 0 antes da execução do Gate 1.

A campanha real só foi autorizada depois dos guards de custo/health estarem ativos.

---

# 100. Estado operacional atual: campanha staged

Campanha:

```text
developmental-dynamics-v1
```

Branch:

```text
research/developmental-dynamics
```

Último HEAD informado **antes da execução autônoma posterior**:

```text
973602e
```

Base científica registrada no manifest no preflight:

```text
b11d064
```

Como Codex pode criar commits locais de reports durante execução, o HEAD final deve sempre ser lido do repositório antes de qualquer análise publicada.

---

# 101. Gate 1 em detalhes

Planejamento informado no preflight:

```text
paired seeds: 1..10
conditions: private, shared
seed 1: reused campaign-compatible pair
new runs: 18
new logical completions: 10,080
nominal expected cost: US$0.363148
hard ceiling: US$1.00
physical-attempt ceiling: 12,600
```

Cada baseline run:

```math
560
```

logical completions:

```math
80\text{ interaction}
+
480\text{ probes}.
```

---

# 102. O que significa “human-gated”

Automação pode decidir:

```text
run already exists?
run health complete?
retry technically allowed?
budget remains?
```

Automação **não** pode decidir:

```text
hypothesis worked?
run Gate 2?
choose random routing?
choose long horizon?
change scientific config?
```

Isso evita adaptive scientific storytelling baseado nos resultados que acabaram de aparecer.

---

# 103. Gate 2

Estado:

```text
LOCKED
```

Meta:

```math
50\text{ paired seeds total}.
```

Incremental previsto no preflight:

```text
seeds 11..50
80 new runs
44,800 logical completions
estimated cost ≈ US$1.613992
```

Gate 2 não é “a próxima etapa obrigatória”.

É uma opção caso Gate 1 mostre que vale comprar uma distribuição mais densa de trajetórias.

---

# 104. Experimentos candidatos preservados, mas bloqueados

## Random routing

Pergunta:

> private experience sozinho produz diferenciação ou precisamos do feedback competence/confidence → assignment?

## Long horizon

Pergunta:

> $t=20$ é estado estável ou transitório?

## Softmax routing

Pergunta:

> greedy selection pressure transforma diferenciação em fixation?

## Feedback locality

Pergunta:

> como $\lambda$ controla o regime?

## Memory capacity

Pergunta:

> finite memory é o trade-off que possibilita niches?

## Interventions

Pergunta:

> onde a role vive e como ela se regenera?

A decisão será orientada pelo Gate 1.

---

# 105. Health gate: ciência começa depois dele

Classificações operacionais atuais:

### CLEAN

100% logical coverage, sem technical retry/error.

### RECOVERED / WARNING

100% logical coverage, mas alguma falha técnica foi recuperada.

### INVALID / INCOMPLETE

faltam logical completions.

Para paired inference principal:

```math
\text{private complete}
\land
\text{shared complete}.
```

Se uma metade é invalid, o pair é incomplete.

---

# 106. Seed 1: provenance

A campanha staged informa um **seed-1 pair campaign-compatible** que pode ser reutilizado.

Não confundir isso com os primeiros artifacts exploratórios antigos que tiveram problemas de coverage/runtime.

Quando o relatório final for produzido, a análise deve mostrar:

1. todos os 10 pares;
2. sensitivity usando apenas newly-generated campaign pairs, excluindo seed 1.

Isso evita discussão de provenance.

---

# 107. Snapshot conhecido do seed 3 durante Gate 1

Enquanto a campanha estava em execução, foi observado:

## Private seed 3

```text
routing counts: 8 / 5 / 2 / 5
memory counts:  8 / 5 / 2 / 5
normalized utilization entropy: 0.9305
normalized task-agent MI: 0.3811
normalized HSE: 0.3618
oracle gain: 0.2000
observed cost: US$0.01620620
```

## Shared seed 3

```text
routing counts: 4 / 7 / 5 / 4
memory counts: 20 / 20 / 20 / 20
normalized utilization entropy: 0.9794
normalized task-agent MI: 0.1939
normalized HSE: 0.0819
oracle gain: 0.0000
observed cost: US$0.01893552
```

### Interpretação permitida

No terminal final desse pair, private apresentou HSE final e oracle gain maiores.

### Interpretação ainda proibida

Não sabemos desse snippet, sozinho:

- $HSE(0)$;
- $HSE(10)$;
- $\Delta HSE$;
- $\Phi(t)$;
- $d_{\mathrm{eff}}$;
- MI acima do null;
- alignment;
- competence structure.

Logo **não transformar esse snapshot em “replicou” antes do report agregado**.

---

# 108. O relatório Gate 1 deve responder estas 15 perguntas

1. Em quantos paired seeds $D_s(20)>0$?
2. O efeito é consistente ou seed-dependent?
3. $\Phi$ conta a mesma história que HSE?
4. $d_{\mathrm{eff}}$ sugere um único eixo ou múltiplos niches?
5. Private reduz utilization sistematicamente?
6. MI excede seu permutation null?
7. A competence matrix adquire estrutura por mundo?
8. O routing alinha com essa competência?
9. Oracle gain/complementarity aumenta?
10. Actual team accuracy melhora?
11. Labels crus permanecem exchangeable across runs?
12. $t=20$ parece estável ou transitório?
13. Winner-take-all é comum?
14. Incluir/excluir seed 1 muda a conclusão?
15. Health/latency/retries diferem por condition?

Essas perguntas definem a próxima decisão.

---

# 109. Possíveis Gate 1 outcomes e próximo experimento natural

## Caso 1 — HSE e $\Phi$ sobem, routing task-specific e aligned

Interpretação:

> strong candidate for functional differentiation.

Próximo passo provável:

- mais seeds (Gate 2);
- depois causal interventions.

---

## Caso 2 — HSE sobe, $\Phi$ não

Interpretação:

> behavioral divergence without stable competence differentiation.

Próximo passo:

- entender probe/noise/memory dynamics;
- não escalar cegamente.

---

## Caso 3 — $\Phi$ sobe, $d_{\mathrm{eff}}\approx1$, utilization cai

Interpretação:

> global dominance/fixation plausible.

Próximo experimento:

- random or softmax routing;
- selection-pressure study.

---

## Caso 4 — private e shared similares

Interpretação:

> feedback locality may not be the main mechanism.

Próximo passo:

- revisit task learnability;
- memory influence;
- stochastic baseline.

---

## Caso 5 — curves ainda mudando em $t=20$

Próximo experimento:

- long horizon.

---

## Caso 6 — estrutura forte, mas $\eta_{\mathrm{route}}\le0$

Interpretação:

> specialists may exist but router fails to exploit them.

Próximo passo:

- routing mechanism comparison.

---

# 110. A pergunta de performance final

Se o orientador perguntar:

> “No fim, isso melhora uma tarefa?”

A resposta correta é:

> Isso é uma camada separada da pergunta de desenvolvimento, mas sim: precisamos testar utility.

Primeiro:

```math
\text{Does structure emerge?}
```

Depois:

```math
\text{Is the structure useful?}
```

Performance real:

```math
A_{\mathrm{team,heldout}}
```

versus:

- best single agent;
- random routing;
- shared condition;
- domain oracle;
- item oracle;
- eventualmente manually specialized control.

---

# 111. Por que não adicionar colaboração agora

Se colocarmos agentes para conversar, introduzimos:

- persuasion;
- consensus;
- shared context;
- information aggregation;
- communication topology.

Isso tornaria difícil saber se a diferenciação veio do task-allocation feedback original.

Primeiro estudar:

```math
\text{allocation society}.
```

Depois:

```math
\text{collaborative society}.
```

---

# 112. A versão mais elegante do “paper grande”

O trabalho pode ser organizado em três atos.

## Act I — Development

```math
B\to B(t).
```

Pergunta:

> de onde vêm roles?

## Act II — Identity

Memory swap/transplant.

Pergunta:

> onde uma role vive?

## Act III — Regeneration

Ablation/replacement.

Pergunta:

> uma sociedade pode restaurar uma função depois de perder seu ocupante?

Isso cria uma narrativa muito mais forte do que “specialization experiment”.

---

# 113. O papel do minimal model no paper

O minimal model não deve ser calibrado retrospectivamente apenas para reproduzir plots.

O ideal:

```text
derive mechanism
      ↓
predict qualitative regime
      ↓
run LLM experiment
      ↓
compare
```

Exemplo:

> Se memory capacity cair, o modelo prediz maior niche competition.

Então testamos.

Essa ordem transforma matemática em teoria preditiva.

---

# 114. Matemática potencialmente publicável

A direção mais rica é estudar uma dinâmica em:

```math
(\Delta^{K-1})^N
```

com symmetry group:

```math
S_N.
```

Questões:

- symmetric fixed points;
- asymmetric fixed points;
- stability eigenmodes;
- coexistence vs fixation;
- dependence on $\lambda,\beta,K_m,N,K$;
- finite-size fluctuations;
- metastability;
- recovery dynamics after perturbation.

Se houver uma bifurcação real no minimal model, podemos perguntar se a sociedade LLM exibe um analogue qualitativo.

Não inverter a lógica e chamar qualquer curva brusca de phase transition.

---

# 115. Como explicar o projeto do zero para alguém de física

“Tenho $N$ subsistemas inicialmente exchangeable. Cada um possui um estado interno que evolui por experiências. Uma variável global de assignment distribui estímulos entre os subsistemas. O assignment depende do comportamento corrente dos subsistemas, criando feedback. Quero saber se o manifold simétrico é estável, quais modos de perturbação crescem, quais macrostates aparecem e se eles são funcionais. Depois faço interventions para testar onde esses macrostates estão armazenados.”

Essa descrição quase não depende da palavra LLM.

Isso é um bom sinal da generalidade matemática.

---

# 116. Como explicar do zero para alguém de ML

“São quatro cópias do mesmo model checkpoint com persistent context separado. Um router baseado em confidence decide quem recebe feedback. Private vs shared controla se o estado dos copies pode divergir. Em checkpoints avaliamos todos no mesmo probe set e medimos behavioral/competence differentiation e whether allocation exploits the resulting competence.”

---

# 117. Como explicar do zero para alguém não técnico

“Quatro pessoas começam com o mesmo treinamento e sem cargo. O sistema distribui trabalhos. Dependendo de quem recebe feedback, histórias diferentes podem fazer pessoas iguais virarem especialistas diferentes — ou fazer uma só pessoa virar dominante. Nós queremos medir qual dessas organizações aparece, por quê, e o que acontece se retirarmos ou trocarmos um especialista.”

---

# 118. Referências verificadas e por que cada uma importa

## Huot, Kaisers & Lapata (2026)

**When is Routing Meaningful? Diversity and Robustness in Language Model Societies.** arXiv:2607.09197.

Usar para:

- $B$;
- HSE em LM societies;
- routing robustness;
- static limitation;
- homogeneous-initialization future direction.

## Balch (2000)

**Hierarchic Social Entropy: An Information Theoretic Measure of Robot Group Diversity.** *Autonomous Robots* 8(3):209–237. DOI: 10.1023/A:1008973424594.

Usar para:

- origem da HSE;
- multiscale taxonomic entropy.

## Jacobs, Jordan, Nowlan & Hinton (1991)

**Adaptive Mixtures of Local Experts.** *Neural Computation* 3(1):79–87. DOI: 10.1162/neco.1991.3.1.79.

Usar para:

- assignment/gating participando da formação de expertise.

## Jordan & Jacobs (1994)

**Hierarchical Mixtures of Experts and the EM Algorithm.** *Neural Computation* 6(2):181–214. DOI: 10.1162/neco.1994.6.2.181.

Usar para:

- probabilistic gating;
- latent expert responsibilities;
- hierarchical expert decomposition.

## Krogh & Vedelsby (1994)

**Neural Network Ensembles, Cross Validation, and Active Learning.** NeurIPS 7.

Usar para:

- disagreement/diversity só é útil em conjunto com individual quality.

## Theraulaz, Bonabeau & Deneubourg (1998)

**Response Threshold Reinforcement and Division of Labour in Insect Societies.** *Proceedings of the Royal Society B* 265(1393):327–332. DOI: 10.1098/rspb.1998.0299.

Usar para:

- response thresholds;
- self-reinforcement;
- specialists from initially similar individuals;
- removal/reintroduction motivation.

## Beshers & Fewell (2001)

**Models of Division of Labor in Social Insects.** *Annual Review of Entomology* 46:413–440. DOI: 10.1146/annurev.ento.46.1.413.

Usar para:

- broader modeling taxonomy of social-insect division of labor.

## Pemantle (2007)

**A Survey of Random Processes with Reinforcement.** *Probability Surveys* 4:1–79. arXiv:math/0610076.

Usar para:

- reinforced-process intuition;
- path dependence / lock-in.

## Bettini, Shankar & Prorok (2025)

**System Neural Diversity: Measuring Behavioral Heterogeneity in Multi-Agent Learning.** *JMLR* 26(163):1–27.

Usar para:

- modern multi-agent behavioral diversity;
- diversity vs task performance/resilience.

## RouterBench — Hu et al. (2024)

**RouterBench: A Benchmark for Multi-LLM Routing System.** arXiv:2403.12031.

Usar para:

- modern external LLM routing context.

## RouteLLM — Ong et al. (2025)

**RouteLLM: Learning to Route LLMs from Preference Data.** ICLR 2025.

Usar para:

- strong-vs-weak model routing / quality-cost optimization.

## MasRouter — Yue et al. (2025)

**MasRouter: Learning to Route LLMs for Multi-Agent Systems.** ACL 2025. DOI: 10.18653/v1/2025.acl-long.757.

Usar para:

- routing extended to roles/collaboration/model choice in MAS.

## Dochkina (2026)

**Drop the Hierarchy and Roles: How Self-Organizing LLM Agents Outperform Designed Structures.** arXiv:2603.28990.

Usar para:

- novelty positioning: spontaneous role/self-organization already has contemporary evidence.

Tratar como preprint recente, não como settled literature.

## Pappu et al. (2026)

**Multi-Agent Teams Hold Experts Back.** arXiv:2602.01011.

Usar para:

- expertise existence vs expertise utilization.

## Deep Sets — Zaheer et al. (2017)

**Deep Sets.** NeurIPS 2017. arXiv:1703.06114.

Usar futuramente para:

- permutation-invariant/equivariant learned representations.

## Set Transformer — Lee et al. (2019)

**Set Transformer: A Framework for Attention-based Permutation-Invariant Neural Networks.** ICML 2019, PMLR 97:3744–3753.

Usar futuramente para:

- relational social-role embedding on unordered agent sets.

## Tishby, Pereira & Bialek (1999)

**The Information Bottleneck Method.** 37th Allerton Conference.

Usar apenas como inspiração para:

- compressed predictive macrostate.

---

# 119. Bibliographic warning

A literatura de self-organizing LLM agents está mudando muito rápido em 2026.

Antes de uma submission:

- refazer systematic search;
- checar papers publicados após agosto/2026;
- procurar direct competitors para “homogeneous initialization + role dynamics + causal interventions”;
- não fazer claim “first” sem revisão dedicada.

---

# 120. Guia de leitura recomendado desta versão

Se o objetivo é **entender tudo antes do orientador**, faça quatro passagens.

## Passagem 1 — história

Leia:

- começo do documento;
- source paper;
- $B\to B(t)$;
- private/shared;
- “functional structure”.

Tente responder sem olhar:

> “Qual pergunta o paper original faz e qual pergunta nós adicionamos?”

## Passagem 2 — métricas

Domine:

```math
B,
HSE,
A,
\Phi,
d_{\mathrm{eff}},
H(R),
I(C;R),
\eta_{\mathrm{route}},
\Delta_{\mathrm{comp}}.
```

Para cada uma saiba responder:

1. qual input usa;
2. o que mede;
3. um caso em que ela engana.

## Passagem 3 — dinâmica

Domine:

```math
S_{t+1}\sim K_\lambda(\cdot\mid S_t,Z_t),
```

exchangeability, permutation symmetry, simplex e reinforcement.

## Passagem 4 — paper grande

Entenda:

- memory transplant;
- ablation;
- replacement;
- regeneration;
- minimal model;
- theory → prediction → experiment.

---

# 121. Quiz de auto-checagem

Se você entendeu o projeto, deve conseguir responder estas perguntas.

1. Por que $HSE(0)>0$ não invalida homogeneous initialization?
2. Qual a diferença entre $B(t)$ e $A(t)$?
3. Por que $\Phi>0$ não prova division of labor?
4. O que $d_{\mathrm{eff}}\approx1$ sugere?
5. Como random routing pode ter $H(R)$ máximo e MI quase zero?
6. Como MI pode ser alta e routing ser ruim?
7. O que $\eta_{\mathrm{route}}$ tenta corrigir conceitualmente?
8. Oracle gain mede performance real?
9. Por que raw agent labels não podem ser averaged diretamente across seeds?
10. Qual é a diferença entre within-run asymmetry e ensemble symmetry?
11. Por que finite memory aparece como simplex?
12. O que é o symmetric fixed point do mean-field shared?
13. Por que reinforcement puro tende a monopoly?
14. Qual é a ponte com response-threshold models?
15. O que memory swap testa causalmente?
16. O que ablation/replacement testa que memory swap não testa?
17. Por que Gate 2 não pode ser liberado automaticamente por HSE?
18. O que random routing isolaria?
19. Quando long horizon vale o custo?
20. Qual é o maior overclaim que devemos evitar?

Respostas resumidas aparecem ao longo do documento.

---

# 122. Respostas do quiz em uma linha

1. Stochastic decoding gera diferenças amostrais apesar de exchangeability.
2. $B$ é item-level behavior; $A$ é competence agregada por niche.
3. Um global winner também gera competence variance.
4. Um eixo dominante de diferenciação.
5. Distribui trabalho sem depender da tarefa.
6. Pode mapear cada task consistentemente ao agente errado.
7. Separar task structure de competence exploitation.
8. Não; mede headroom/potential.
9. Labels são symmetry-equivalent.
10. Runs podem quebrar simetria sem privilegiar labels no ensemble.
11. Frações de capacidade/memória somam 1.
12. Todos convergem à task distribution $\rho$.
13. Advantage → more traffic → more advantage.
14. Task execution muda future propensity.
15. Se role acompanha acquired memory/state.
16. Se a organização recria uma função sem o ocupante original.
17. Evitar adaptive scientific stopping/confirmation.
18. Reinforcement competence→routing vs mere private history.
19. Quando $t=20$ ainda parece transitório.
20. “HSE aumentou, portanto demonstramos emergent specialization.”

---

# 123. Checklist para conversar com o orientador

Antes da reunião, saiba desenhar no quadro:

### 1.

```math
B\to B(t)
```

### 2.

```math
S_{t+1}\sim K_\lambda(\cdot\mid S_t,Z_t)
```

### 3.

```math
A(t)\to\Phi(t)
```

### 4.

```math
Q=XX^\top/K\to d_{\mathrm{eff}}
```

### 5.

```math
H(R),\quad I(C;R)
```

### 6.

```math
\eta_{\mathrm{route}}
```

### 7.

```math
x_i\in\Delta^{K-1}
```

E consiga explicar verbalmente:

> HSE = “ficaram diferentes?”  
> $\Phi$ = “ficaram diferentemente competentes?”  
> spectrum = “em quantos eixos?”  
> MI = “allocation depende da task?”  
> alignment = “allocation escolhe quem é bom?”  
> oracle gain = “há complementaridade disponível?”  
> interventions = “onde a role está armazenada?”

---

# 124. O paper em uma frase em cada estágio

## Source paper

> When is routing structurally meaningful among a fixed set of actors?

## Nosso primeiro experimento

> Can routing-mediated histories make initially exchangeable actors behaviorally different?

## Nossa versão atual

> Under what dynamics does this differentiation become stable functional organization?

## Paper grande

> How do roles form, move and regenerate in initially homogeneous LM societies?

---

# 125. Síntese atualizada final

A história inteira pode ser comprimida em:

```math
\boxed{
\text{static diversity}
\to
\text{developmental diversity}
\to
\text{functional differentiation}
\to
\text{role identity}
\to
\text{regeneration}
}
```

Com as perguntas correspondentes:

```math
\boxed{
B
\to
B(t)
\to
A(t)
\to
\text{interventions}
\to
\text{recovery}
}
```

E com um princípio metodológico que deve permanecer do começo ao fim:

> **Não confundir uma mudança em uma métrica com a emergência da estrutura que queremos explicar.**

O objetivo não é maximizar HSE, nem fazer um router performar melhor a qualquer custo.

O objetivo é entender:

```math
\boxed{
\text{quando diferenças microscópicas se tornam organização funcional macroscópica,}
}
```

```math
\boxed{
\text{onde essa organização vive e se ela pode sobreviver à perda de seus componentes.}
}
```

Essa é, hoje, a versão mais completa da ideia do projeto.

---

## Addendum — Theory V1: prediction before the next society

Em 12 de agosto de 2026 o projeto separou explicitamente os dados de
desenvolvimento da próxima tentativa de teste prospectivo. Todos os resultados
anteriores — inclusive a curva de plasticidade local e a análise reparada da
sociedade — são **DEVELOPMENT**: motivam e informam a teoria, mas não contam como
confirmação independente dela.

Theory V1 congela um modelo efetivo local. A resposta microscópica a uma troca
de um slot de memória é estimada por $K^{(k)}$, o operador centrado é
$T_k = P_K (K^{(k)})^\top D_\rho P_K$, a retenção mean-field é
$r(k,q)=1-[q+(1-q)/N]/k$, e a dinâmica linearizada é
$J = rI + (1-q)((1-\varepsilon)\beta/N)T_k$. $\Psi_{\mathrm{spec}}$ continua sendo a medida primária de
formação de interação agente×nicho; utilidade coletiva, routing e HSE não podem
substituí-la.

O protocolo congelado define duas ecologias, sementes novas, três capacidades
de memória e uma grade social fixa. O plano possui 26.112 chamadas MICRO para
parametrização e 186.368 chamadas MACRO para confirmação social. Antes de
qualquer chamada MACRO, as estimativas e previsões precisam estar commitadas e
seladas. Nenhum resultado Theory V1 foi coletado nesta preparação; a
implementação offline e os testes estão em `src/emergent_specialization/theory_v1/`
e `docs/theory/`. Se o custo forecast exceder o teto, o protocolo será
bloqueado, não reduzido nem adaptado.
