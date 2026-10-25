# Linguagem FORGE v0.1

Uma instrução por linha. Texto entre aspas identifica projeto, cena e objetos. A versão inicial suporta uma cena por arquivo.

## Declarações

    project "MeuProjeto"
    scene "Intro" mode 2d fps 30 duration 3
    object "Bola" circle color "#58d6ff" at (40,120,0) size (32,32)
    animate "Bola" move from (40,120,0) to (320,120,0) from 0s to 3s ease smooth

O modo pode ser 2d ou 3d. FPS aceita 1-240 e duração aceita valores maiores que 0 até 600 s. Cores seguem formato hexadecimal #RRGGBB.

## Tipos de objeto

circle, box, sphere, cone e torus. Use size para dimensões de tela 2D e scale para escala 3D. Posição usa três valores; dimensões usam dois ou três valores.

## Animações

move altera posição, rotate altera rotação e scale altera tamanho/escala. Os tempos são segundos, o fim deve ser maior que o início e não pode ultrapassar a duração da cena. ease linear preserva a taxa de interpolação; ease smooth aplica suavização nas extremidades.

## Limites atuais

Sem scripts arbitrários, física, rigs, áudio, partículas, múltiplas cenas, loops declarativos ou renderização/exportação de vídeo. Um script inválido deve produzir erro com número da linha e não apagar o texto digitado.
