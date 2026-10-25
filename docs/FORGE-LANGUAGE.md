# Linguagem FORGE — especificação inicial

FORGE é uma linguagem declarativa própria para descrever uma cena e animar propriedades ao longo do tempo. No MVP, não é uma linguagem geral e **não executa JavaScript**.

## Regras

- Um comando por linha; linhas vazias e linhas iniciadas por // são ignoradas.
- Os atributos usam o formato **chave=valor**.
- Nomes de objetos começam por letra ou _ e aceitam letras, números, _ e -.
- Coordenadas 2D usam origem no canto superior esquerdo; x cresce para a direita e y para baixo.
- Rotações 2D e 3D são expressas em radianos.
- Valores de cor aceitam #RGB ou #RRGGBB.
- Keyframes interpõem propriedades numéricas linearmente; valores de texto e cor ficam com o valor anterior até o keyframe seguinte.
- Os comandos são validados por uma lista permitida; comandos desconhecidos geram erro.

## Comandos

### scene

~~~forge
scene "Título da cena" fps=24 width=960 height=540
~~~

fps é limitado a 1–120; largura e altura são limitadas a 64–4096.

### background

~~~forge
background color=#0b1020
~~~

### Objetos

~~~forge
circle orb x=120 y=270 radius=28 color=#65e8d4
rect floor x=0 y=440 width=960 height=100 color=#17233a
text title x=40 y=60 value="MOTIONFORGE" size=28 color=#eaf2ff
cube core x=0 y=0 z=0 size=1.2 color=#65e8d4
~~~

circle precisa de radius positivo; rect precisa de largura e altura positivas; cube precisa de size positiva.

### Quadros-chave 2D

~~~forge
key orb at=0 x=120 y=270 scale=1
key orb at=24 x=480 y=154 scale=1.35
key orb at=48 x=820 y=270 scale=1
~~~

### Quadros-chave 3D

~~~forge
key3 core at=0 rotationY=0 rotationX=0
key3 core at=48 rotationY=6.28 rotationX=1.0
~~~

key3 é exclusivo para cube. Propriedades animáveis no MVP: x, y, z, scale, rotation, rotationX, rotationY, rotationZ, opacity e color.

## Limites do MVP

Não há variáveis, loops, funções, expressões matemáticas, rigging, esqueleto, partículas, renderização final de vídeo nem interpolação Bézier. Os comandos inválidos são reportados pela linha. Próximas etapas devem adicionar AST tipada, mensagens de validação mais específicas, curvas easing, exportação de sequência e, depois, exportação de vídeo.
