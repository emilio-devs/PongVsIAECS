import pygame
import random
import math

# Inicializar Pygame
pygame.init()

# Dimensiones de la pantalla
WIDTH, HEIGHT = 800, 600
INTERFACE_HEIGHT = 50  # Altura de la interfaz superior
GAME_AREA_HEIGHT = HEIGHT - INTERFACE_HEIGHT

# Colores
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
GREEN = (0, 255, 0)
LIME = (0, 255, 0)

BASE_CANNON_COLOR = (255, 215, 0)
TOP_CANNON_COLOR = (255, 165, 0)

# Limite fps por defecto
FPS_LIMIT_DEFAULT = 60
DEFAULT_BALL_SPEED = 100
MAX_BALL_SPEED = 1250

# Clase base para todas las entidades del juego
class GameEntity:
    def __init__(self, x, y, width, height, colisionable=True):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.colisionable = colisionable

    def update(self, delta_time, control_system):
        """Actualizar la entidad (para que cada entidad lo implemente)"""
        raise NotImplementedError

    def draw(self, screen):
        """Dibujar la entidad en pantalla"""
        pass

    def is_colliding(self, other):
        """Verificar si esta entidad está colisionando con otra"""
        if not self.colisionable or not other.colisionable:
            return False
        return (self.x < other.x + other.width and
                self.x + self.width > other.x and
                self.y < other.y + other.height and
                self.y + self.height > other.y)

class Score(GameEntity):
    def __init__(self, x, y, width, height, text, font=None):
        super().__init__(x, y, width, height, colisionable=False)
        # Fuente para el texto
        if font:
            self.font = font
        else:
            self.font = pygame.font.SysFont('Arial', 30)
        self.value = 0
        self.text = text  # Texto que precede al valor de la puntuación, como "Jugador: " o "IA: "

    def update(self, delta_time, control_system):
        # El puntaje no cambia en cada frame, lo hace en base a eventos específicos
        pass

    def increment(self):
        self.value += 1  # Aumentar el puntaje

    def draw(self, screen):
        score_text = f"{self.text} {self.value}"
        text_surface = self.font.render(score_text, True, WHITE)
        screen.blit(text_surface, (self.x, self.y))

class Bullet(GameEntity):
    def __init__(self, x, y, width, height, speed=500, direction='up'):
        super().__init__(x, y, width, height, colisionable=True)
        self.speed = speed
        self.destroyed = False
        self.direction = direction

    def update(self, delta_time, control_system):
        # Mover la bala hacia arriba
        if self.direction == 'up':
            self.y -= self.speed * delta_time
        else:
            self.y += self.speed * delta_time

        # Verificar colisiones con el paddle enemigo
        for entity in control_system.entities:
            if isinstance(entity, Paddle) and ((self.direction == 'up' and entity.is_enemy) or (self.direction == 'down' and not entity.is_enemy)):
                if self.is_colliding(entity):
                    self.handle_collision(entity)

        # Destruir la bala si sale de la pantalla
        if self.y <= INTERFACE_HEIGHT or self.y >= GAME_AREA_HEIGHT:
            self.destroyed = True

    def handle_collision(self, enemy_paddle):
        # Eliminar el primer bloque con el que colisiona
        for block in enemy_paddle.blocks:
            if block.is_colliding(self):
                block.destroy()
                self.destroyed = True
                break

    def draw(self, screen):
        pygame.draw.rect(screen, (255, 0, 0), (self.x, self.y, self.width, self.height))  # Rojo para la bala

class PaddleBlock(GameEntity):
    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, colisionable=True)        
        self.x = x
        self.y = y
        self.color = WHITE
        self.width = width
        self.height = height
        self.destroyed = False
    
    def update(self, delta_time, control_system):
        pass

    def draw(self, screen):
        if not self.destroyed:
            pygame.draw.rect(screen, self.color, (int(self.x), int(self.y), int(self.width), int(self.height)))

    def set_color_pos_and_size(self, color, x, y, width, height):
        self.color = color
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    def repair(self):
        self.destroyed = False
        self.colisionable = True 

    def destroy(self):
        self.destroyed = True
        self.colisionable = False


class Paddle(GameEntity):

    def __init__(self, x, y, width, height, control_component, is_enemy=False):
        super().__init__(x, y, width, height, colisionable=True)        
        self.x = x
        self.y = y
        self.original_speed = 2000
        self.current_speed = self.original_speed
        self.original_width = width
        self.width = self.original_width
        self.height = height
        self.control_component = control_component
        self.original_color = WHITE
        self.color = self.original_color
        self.is_enemy = is_enemy

        self.is_frozen = False
        self.freeze_timer = 0

        self.is_slowed = False
        self.slow_down_timer = 0

        self.width_extended = False
        self.extra_width_timer = 0
        self.extra_width_duration = 0

        # Inicializar los rectángulos con valores por defecto
        self.blocks = [
            PaddleBlock(0, 0, 0, 0),
            PaddleBlock(0, 0, 0, 0),
            PaddleBlock(0, 0, 0, 0),
            PaddleBlock(0, 0, 0, 0),
            PaddleBlock(0, 0, 0, 0)
        ]
        self.cannon_base = PaddleBlock(0, 0, 0, 0)
        self.cannon_top = PaddleBlock(0, 0, 0, 0)

        self.has_cannon = False
        self.bullet = None
        self.cannon_timer = 0

        if self.is_enemy:
            self.invert_paddle()

    def freeze(self, duration):
        self.is_frozen = True
        self.freeze_timer = duration

    def slow_down(self, speed, duration):
        # Reducir la velocidad de movimiento
        self.is_slowed = True
        self.current_speed = speed
        self.slow_down_timer = duration
        self.color = (105, 105, 105)

    def increase_width(self, extra_width, duration):
        self.width_extended = True
        self.width += extra_width
        self.extra_width_timer = duration
        self.extra_width_duration = duration

    def add_cannon(self, duration):
        """Añadir un cañón al paddle del jugador."""
        self.has_cannon = True  
        self.cannon_timer = duration      

    def shoot_bullet(self):
        if self.has_cannon and not self.bullet:
            # Crear una bala en el centro superior del paddle
            bullet_x = self.x + self.width / 2 - 5  # Ajuste para centrar la bala
            if self.is_enemy:
                bullet_y = self.y + self.height + 10  # Para la IA, disparar hacia abajo
                new_bullet = Bullet(bullet_x, bullet_y, 10, 20, direction='down')  # Direccion hacia abajo
            else:
                bullet_y = self.y - 10
                new_bullet = Bullet(bullet_x, bullet_y, 10, 20, direction='up')  # Direccion hacia arriba
            self.bullet = new_bullet


    def invert_paddle(self):
        """Invertir la orientación del paddle para la IA (arriba)."""
        for rect in self.blocks:
            # Invertimos el paddle reflejándolo verticalmente
            rect.y = self.y - (rect.y - self.y + rect.height) + self.height          
        
        if self.has_cannon:
            cannon_base_y = self.y + self.height 
            cannon_top_y = self.y + self.height + 10
            self.cannon_base.set_color_pos_and_size(BASE_CANNON_COLOR, self.x + self.width / 2 - 10, cannon_base_y, 20, 10)
            self.cannon_top.set_color_pos_and_size(TOP_CANNON_COLOR, self.x + self.width / 2 - 5, cannon_top_y, 10, 10)

    def regenerate_blocks(self):
        for rect in self.blocks:
            rect.repair()


    def update(self, delta_time, control_system):
         # Si el paddle está congelado, reducir el temporizador
        if self.is_frozen:
            self.freeze_timer -= delta_time
            if self.freeze_timer <= 0:
                self.is_frozen = False

        
        # Si el paddle está ralentizado, reducir el temporizador
        if self.is_slowed:
            self.slow_down_timer -= delta_time
            if self.slow_down_timer <= 0:
                self.is_slowed = False
                self.current_speed = self.original_speed  # Restaurar la velocidad original
                self.color = self.original_color

        # Si el paddle está con tamaño extra, reducir el temporizador
        if self.width_extended:
            # Reducir el temporizador de la ampliación del ancho
            self.extra_width_timer -= delta_time
            
            # Tiempo restante como proporción (0 a 1)
            remaining_time_ratio = max(0, self.extra_width_timer / self.extra_width_duration)  # duration es el tiempo total del power-up
            # Comienza la transición de dorado a blanco si quedan menos de 2 segundos
            self.color = (
                int(GOLD[0] * remaining_time_ratio + WHITE[0] * (1 - remaining_time_ratio)),
                int(GOLD[1] * remaining_time_ratio + WHITE[1] * (1 - remaining_time_ratio)),
                int(GOLD[2] * remaining_time_ratio + WHITE[2] * (1 - remaining_time_ratio)),
            )
            
            if self.extra_width_timer <= 0:
                self.width_extended = False
                self.width = self.original_width
                self.color = self.original_color  # Restaurar el color original

        if self.has_cannon:
            self.cannon_timer -= delta_time
            if self.cannon_timer <= 0:
                self.has_cannon = False
        
        if self.bullet:
            self.bullet.update(delta_time, control_system)
            if self.bullet.destroyed:
                self.bullet = None

        # Actualizar la posición del paddle
        if not self.is_frozen:
            self.control_component.update(self, self.current_speed, delta_time, control_system)
        
        central_width = self.width * 0.5  # Hacer el central más prominente
        side_width = self.width * 0.2  # Ajustar los laterales para que sumen bien
        edge_width = self.width * 0.1  # Mantener extremos pequeños

        central_height = self.height * 0.6
        side_height = self.height * 0.5
        edge_height = self.height * 0.35


        self.blocks[0].set_color_pos_and_size(self.color, self.x, self.y + self.height - edge_height, edge_width, edge_height)  # Extremo izq
        self.blocks[1].set_color_pos_and_size(self.color, self.x + edge_width - 2, self.y + self.height / 3, side_width, side_height)  # Izquierdo
        self.blocks[2].set_color_pos_and_size(self.color, self.x + self.width / 2 - central_width / 2, self.y, central_width, central_height)  # Central
        self.blocks[3].set_color_pos_and_size(self.color, self.x + self.width - edge_width - side_width + 2, self.y + self.height / 3, side_width, side_height)  # Derecho
        self.blocks[4].set_color_pos_and_size(self.color, self.x + self.width - edge_width, self.y + self.height - edge_height, edge_width, edge_height)  # Extremo der

        if not self.is_enemy and self.has_cannon:
            self.cannon_base.set_color_pos_and_size(BASE_CANNON_COLOR, self.x + self.width / 2 - 10, self.y - 10, 20, 10)
            self.cannon_top.set_color_pos_and_size(TOP_CANNON_COLOR, self.x + self.width / 2 - 5, self.y - 20, 10, 10)

        # Aplicar la inversión si es el paddle enemigo
        if self.is_enemy:
            self.invert_paddle()

    def draw(self, screen):
        # Dibujar todos los rectángulos del paddle
        for rect in self.blocks:
            rect.draw(screen)

        # Si el paddle está congelado, dibujar triángulos azules a su alrededor
        if self.is_frozen:
            triangle_count = 5  # Número de triángulos a dibujar

            for _ in range(triangle_count):
                # Generar un color azul claro aleatorio para simular diferentes intensidades de hielo
                ice_color = (
                    random.randint(150, 200),  # Rango de azul claro en el componente rojo
                    random.randint(200, 240),  # Rango de azul claro en el componente verde
                    random.randint(230, 255)   # Rango de azul claro en el componente azul
                )

                # Generar puntos aleatorios alrededor del paddle
                triangle = [
                    (self.x + random.uniform(-20, self.width + 20), self.y + random.uniform(-20, self.height + 20)),
                    (self.x + random.uniform(-20, self.width + 20), self.y + random.uniform(-20, self.height + 20)),
                    (self.x + random.uniform(-20, self.width + 20), self.y + random.uniform(-20, self.height + 20))
                ]
                pygame.draw.polygon(screen, ice_color, triangle)

        if self.has_cannon:
            self.cannon_base.draw(screen)
            self.cannon_top.draw(screen)

        if self.bullet:
            self.bullet.draw(screen)

    def is_colliding(self, ball):
        # Verificar colisiones con todos los rectángulos del paddle
        for block in self.blocks:
            if not block.destroyed and block.is_colliding(ball):
                return True
        return False
    
    
class Ball(GameEntity):
    def __init__(self, radius, speed_x=DEFAULT_BALL_SPEED, speed_y=DEFAULT_BALL_SPEED):
        super().__init__(WIDTH // 2, HEIGHT // 2, radius * 2, radius * 2, colisionable=True)
        self.radius = radius
        self.speed_x = speed_x
        self.speed_y = speed_y
        # Dirección inicial como vector unitario (-1 a 1 en X y Y)
        self.dir_x = random.uniform(-1, 1)
        self.dir_y = random.choice([-1, 1])
        self.collided_last_frame = False
        self.randomize_color()
        self.last_paddle_collision = None

    def randomize_color(self):
        self.color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    def spawn(self, control_system):
        self.x, self.y = WIDTH // 2, HEIGHT // 2
        # Dirección inicial aleatoria
        self.dir_x = random.uniform(-1, 1)
        self.dir_y = random.choice([-1, 1])
        self.collided_last_frame = False
        self.speed_x = DEFAULT_BALL_SPEED
        self.speed_y = DEFAULT_BALL_SPEED
        self.randomize_color()
        for entity in control_system.entities:
            if isinstance(entity, Paddle):
                entity.regenerate_blocks()
        
        control_system.game.wave_effect_system.trigger_wave_effect(0.5)

    def update(self, delta_time, control_system):
        # Mover la bola en función de la dirección y la velocidad
        self.x += self.dir_x * self.speed_x * delta_time
        self.y += self.dir_y * self.speed_y * delta_time

        # Verificar colisiones con otras entidades
        collision_occurred = False
        for entity in control_system.entities:
            if entity != self and entity.is_colliding(self):
                if isinstance(entity, Paddle):
                    collision_occurred = True
                    self.last_paddle_collision = entity
                    if not self.collided_last_frame:
                        # Calcular el punto de colisión relativo al paddle
                        relative_intersect_x = (self.x + self.radius) - entity.x
                        normalized_relative_intersect_x = (relative_intersect_x / entity.width) * 2 - 1

                        # Multiplicar la dirección Y por la normal del paddle (invierto solo el componente Y)
                        self.dir_x = normalized_relative_intersect_x
                        self.dir_y = -self.dir_y

                        # Aumentar la velocidad de la bola
                        self.speed_x = min(MAX_BALL_SPEED, self.speed_x + 60)
                        self.speed_y = min(MAX_BALL_SPEED, self.speed_y + 60)

                        self.randomize_color()  

        if not collision_occurred:
            self.collided_last_frame = False
        else:
            self.collided_last_frame = True

        # Colisión con los bordes verticales de la pantalla
        if self.x <= 0 or self.x + self.radius * 2 >= WIDTH:
            self.dir_x = -self.dir_x  # Invertir la dirección horizontal
            self.randomize_color()

        # Verificar si la bola toca los bordes superiores o inferiores
        if self.y <= INTERFACE_HEIGHT:  # La bola toca el límite superior (IA pierde punto)
            for entity in control_system.entities:
                if isinstance(entity, Score) and entity.text == "Jugador:":
                    entity.increment()
                    if entity.value >= 5:
                        control_system.game.game_over = True
                        control_system.game.win_message = "HAS GANADO MENUDO CRACK"

            self.spawn(control_system)  # Reiniciar la bola

        elif self.y + self.radius * 2 >= GAME_AREA_HEIGHT:  # La bola toca el límite inferior (jugador pierde punto)
            for entity in control_system.entities:
                if isinstance(entity, Score) and entity.text == "IA:":
                    entity.increment()
                    if entity.value >= 5:
                        control_system.game.game_over = True
                        control_system.game.win_message = "LA IA GANA"

            self.spawn(control_system)  # Reiniciar la bola

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x + self.radius), int(self.y + self.radius)), self.radius)

# Componente de control del jugador (input del ratón)
class PlayerControlComponent:
    def update(self, paddle, speed, delta_time, control_system):
        mouse_x, _ = pygame.mouse.get_pos()
        target_x = mouse_x - paddle.width / 2
        if paddle.x < target_x:
            paddle.x = min(paddle.x + speed * delta_time, target_x)
        elif paddle.x > target_x:
            paddle.x = max(paddle.x - speed * delta_time, target_x)

# Componente de control por IA (sigue la bola)
class IAControlComponent:
    def __init__(self):
        self.current_offset = 0
        self.life_time = 0

    def update(self, paddle, speed, delta_time, control_system):
        # Buscar la bola en las entidades del sistema de físicas
        self.life_time += delta_time
        ball = None
        for entity in control_system.entities:
            if isinstance(entity, Ball):  # Si encontramos la bola
                ball = entity
                break
        
        # Si encontramos la bola, mover el paddle hacia la bola
        if ball:
            self.current_offset = math.sin(self.life_time) * (paddle.width / 4)
            target_x = ball.x + ball.width / 2 - paddle.width / 2 + self.current_offset  # La IA apunta ligeramente a un lado
            if paddle.x < target_x:
                paddle.x = min(paddle.x + speed * delta_time, target_x)
            elif paddle.x > target_x:
                paddle.x = max(paddle.x - speed * delta_time, target_x)

        if paddle.has_cannon and not paddle.bullet:
            paddle.shoot_bullet()

class PowerUp(GameEntity):
    def __init__(self, x, y, width, height, duration=8):
        super().__init__(x, y, width, height, colisionable=True)
        self.duration = duration  # Tiempo que el power_up estará activo en la pantalla
        self.life_time = 0  # Temporizador para controlar la vida del power_up
        self.font = pygame.font.SysFont('Arial', 20, bold=True)
        self.symbol = self.font.render('!', True, WHITE)
        self.blinking = False
        self.hidden = False
        self.color = (238, 210, 2)
    
    def update(self, delta_time, control_system):
        # Actualizar el temporizador para la duración del power_up
        self.life_time += delta_time
        time_left = self.duration - self.life_time 

        if time_left <= 3:
            self.blinking = True
    
    def draw(self, screen):
        if self.blinking:
            time_left = self.duration - self.life_time

            # Modificar el valor de rojo y el ritmo de parpadeo con base en el tiempo restante
            # Cuanto menos tiempo quede, más rápido será el parpadeo
            blink_rate = (1 - time_left / 3) * 2  # Aumenta de 0 a 5 parpadeos por segundo linealmente

            # Alternar visibilidad del power_up para crear el parpadeo
            if (self.life_time * blink_rate) % 1 < 0.5:
                self.hidden = False # Rojo durante la mitad del ciclo
            else:
                self.hidden = True  # Negro durante la otra mitad del ciclo para el parpadeo

        if not self.hidden:
            # Dibujar un rectángulo rojo con bordes redondeados
            pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height), border_radius=10)

            # Dibujar el símbolo ! en el centro del power_up
            symbol_rect = self.symbol.get_rect(center=(self.x + self.width // 2, self.y + self.height // 2))
            screen.blit(self.symbol, symbol_rect)

class FreezePowerUp(PowerUp):
    def __init__(self, x, y, width, height, duration=8.5):
        super().__init__(x, y, width, height, duration)
        self.symbol = self.font.render('F', True, WHITE)
        self.color = (238, 210, 2)

    def apply_effect(self, power_up_system):
        power_up_taker = power_up_system.ball.last_paddle_collision

        # Congelar el paddle por 2 segundos
        if power_up_taker:
            if power_up_taker == power_up_system.ai_paddle:
                power_up_system.player_paddle.freeze(0.5)
            else:
                power_up_system.ai_paddle.freeze(0.5)

class SlowDownPowerUp(PowerUp):
    def __init__(self, x, y, width, height, duration=8):
        super().__init__(x, y, width, height, duration)
        self.symbol = self.font.render('S', True, WHITE)
        self.color = (105, 105, 105)  # Gris oscuro para ralentización

    def apply_effect(self, power_up_system):
        power_up_taker = power_up_system.ball.last_paddle_collision

        # Reducir la velocidad del paddle por 5 segundos
        if power_up_taker:
            if power_up_taker == power_up_system.ai_paddle:
                power_up_system.player_paddle.slow_down(300, 1)
            else:
                power_up_system.ai_paddle.slow_down(300, 1)


class IncreaseWidthPowerUp(PowerUp):
    def __init__(self, x, y, width, height, duration=8):
        super().__init__(x, y, width, height, duration)
        self.symbol = self.font.render('W', True, WHITE)
        self.color = (50, 205, 50)  # Verde brillante para crecimiento

    def apply_effect(self, power_up_system):
        power_up_taker = power_up_system.ball.last_paddle_collision

        # Reducir la velocidad del paddle por 5 segundos
        if power_up_taker:
            power_up_taker.increase_width(100, 5)        

class CannonPowerUp(PowerUp):
    def __init__(self, x, y, width, height, duration=8):
        super().__init__(x, y, width, height, duration)
        self.symbol = self.font.render('C', True, WHITE)
        self.color = (255, 0, 0)  # Rojo

    def apply_effect(self, power_up_system):
        power_up_taker = power_up_system.ball.last_paddle_collision

        # Añadir un cañón al paddle del jugador
        if power_up_taker:
            power_up_taker.add_cannon(2)

class PowerUpSystem:
    def __init__(self, control_system, ball, player_paddle, ai_paddle):
        self.control_system = control_system
        self.power_up_list = []
        self.ball = ball
        self.player_paddle = player_paddle
        self.ai_paddle = ai_paddle
        self.spawn_time = random.uniform(5, 10)  # Tiempo aleatorio entre 5 y 10 segundos para spawnear
        self.timer = 0  # Temporizador para controlar el spawn
    
    def update(self, delta_time):
        # Incrementar el temporizador
        self.timer += delta_time
        # Cuando el temporizador alcanza el tiempo de spawn, crear un nuevo PowerUp
        if self.timer >= self.spawn_time:
            self.spawn_power_up()
            # Resetear el temporizador y calcular un nuevo tiempo aleatorio
            self.timer = 0
            self.spawn_time = random.uniform(5, 10)
        
        self.check_power_up_collided_with_ball()
        
        # Eliminar los power_ups expirados
        for power_up in self.power_up_list[:]:  # Usar una copia para modificar la lista mientras iteramos
            if(power_up.life_time >= power_up.duration):
                self.remove_power_up(power_up)
        
    def spawn_power_up(self):
        # Spawnear un PowerUp en una posición aleatoria dentro del área de juego
        x = random.randint(50, WIDTH - 100)
        y = random.uniform(INTERFACE_HEIGHT + GAME_AREA_HEIGHT * 0.2, INTERFACE_HEIGHT + GAME_AREA_HEIGHT * 0.7)
        power_up_type = random.choice([FreezePowerUp, SlowDownPowerUp, IncreaseWidthPowerUp, CannonPowerUp])
        new_power_up = power_up_type(x, y, 30, 30)
        self.control_system.add_entity(new_power_up)
        self.power_up_list.append(new_power_up)

    def remove_power_up(self, entity):
        if entity in self.control_system.entities:
            self.control_system.remove_entity(entity)
        
        if entity in self.power_up_list:
            self.power_up_list.remove(entity)
            
    def check_power_up_collided_with_ball(self):
        for power_up in self.power_up_list:
            if power_up.is_colliding(self.ball):
                power_up.apply_effect(self)
                self.remove_power_up(power_up)

# Sistema de físicas que procesa todas las entidades
class ControlSystem:
    def __init__(self, game):
        self.entities = []
        self.game = game

    def add_entity(self, entity):
        self.entities.append(entity)

    def remove_entity(self, entity):
        if entity in self.entities:
            self.entities.remove(entity)

    def update(self, delta_time):
        # Actualizar todas las entidades y verificar colisiones
        for entity in self.entities:
            entity.update(delta_time, self)

# Sistema de físicas que procesa todas las entidades
class DebugSystem:
    def __init__(self, control_system):
        self.control_system = control_system
        self.debugging = False

    def update(self):
        pass

    def draw(self, screen):
        if self.debugging:
            for entity in self.control_system.entities:
                pygame.draw.rect(screen, (255, 0, 0), (entity.x, entity.y, entity.width, entity.height), 1)

    def toggle_debug_mode(self):
        self.debugging = not self.debugging
    
# Sistema de físicas que procesa todas las entidades
class WaveEffectSystem:
    def __init__(self, control_system):
        self.control_system = control_system
        self.wave_effects = []
        self.wave_timer = 0
        self.wave_frequency = 0.5
        self.time_since_last_wave = 0
        self.effect_duration = 0
        self.spawn_waves = False

    def trigger_wave_effect(self, effect_duration, wave_frequency=0.09):
        # Iniciar un nuevo efecto de onda desde los bordes del área de juego
        self.effect_duration = effect_duration
        self.wave_frequency = wave_frequency
        self.spawn_waves = True

    def add_wave(self, color=LIME, speed=50):
        wave_size = 0  # Tamaño inicial de la onda
        offset_color = (
            max(0, min(255, color[0] + random.randint(int(color[0]*-0.8), int(color[0]*0.8)))),  # Ajustar el componente rojo
            max(0, min(255, color[1] + random.randint(int(color[1]*-0.8), int(color[1]*0.8)))),  # Ajustar el componente verde
            max(0, min(255, color[2] + random.randint(int(color[2]*-0.8), int(color[2]*0.8))))   # Ajustar el componente azul
        )  
        speed = random.uniform(speed - speed * 0.3, speed + speed * 0.3)
        self.wave_effects.append({'size': wave_size, 'color': offset_color, 'speed': speed})

    def update(self, delta_time):
        if self.spawn_waves:
            self.effect_duration -= delta_time
            self.time_since_last_wave += delta_time
            # Generar nueva onda en la frecuencia dada
            if self.time_since_last_wave >= self.wave_frequency:
                self.add_wave()
                self.time_since_last_wave = 0
            # Detener la generación de ondas cuando termine el tiempo de efecto
            if self.effect_duration <= 0:
                self.spawn_waves = False

        for wave in self.wave_effects:
            # Incrementar el tamaño de la onda para que se mueva hacia adentro
            wave['size'] += (wave['speed'] + wave['speed'] * random.uniform(0, 0.2)) * delta_time

        # Eliminar las ondas que ya no son visibles (cuando cubren todo el área de juego)
        self.wave_effects = [wave for wave in self.wave_effects if wave['size'] <= 20]


    def draw(self, screen):
        for wave in self.wave_effects:
            wave_rect = pygame.Rect(
                wave['size'],  # Margen izquierdo
                INTERFACE_HEIGHT + wave['size'],  # Margen superior
                WIDTH - wave['size'] * 2,  # Ancho del rectángulo
                GAME_AREA_HEIGHT - wave['size'] * 2  # Altura del rectángulo
            )
            pygame.draw.rect(screen, wave['color'], wave_rect, 2)  # Dibujar borde blanco


# Definir la clase Game
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Pong con IA y Jugador')
        self.clock = pygame.time.Clock()
        self.fps_limit = FPS_LIMIT_DEFAULT

        # Sistema de físicas
        self.control_system = ControlSystem(self)
        self.debug_system = DebugSystem(self.control_system)
        self.wave_effect_system = WaveEffectSystem(self.control_system)

        # Objetos del juego
        self.ball = Ball(radius=15)

        # Crear los paddles
        self.player_paddle = Paddle(x=(WIDTH - 100) / 2, y=GAME_AREA_HEIGHT - 40, width=150, height=35,
                                    control_component=PlayerControlComponent())  # Jugador hacia arriba
        self.ai_paddle = Paddle(x=(WIDTH - 100) / 2, y=INTERFACE_HEIGHT + 40, width=150, height=35,
                                control_component=IAControlComponent(), is_enemy=True)  # IA hacia abajo


        # Crear los puntajes
        self.player_score = Score(x=10, y=10, width=100, height=30, text="Jugador:")
        self.ai_score = Score(x=WIDTH - 150, y=10, width=100, height=30, text="IA:")

        # Añadir entidades al sistema de fisicas
        self.control_system.add_entity(self.ball)
        self.control_system.add_entity(self.player_paddle)
        self.control_system.add_entity(self.ai_paddle)
        self.control_system.add_entity(self.player_score)
        self.control_system.add_entity(self.ai_score)

        self.power_up_system = PowerUpSystem(self.control_system, self.ball, self.player_paddle, self.ai_paddle)
        self.game_over = False
        self.win_message = ""


    def reset_game(self):
        self.game_over = False
        self.win_message = ""
        self.player_score.value = 0
        self.ai_score.value = 0
        self.ball.spawn(self.control_system)
        self.player_paddle.regenerate_blocks()
        self.ai_paddle.regenerate_blocks()


    def run(self):
        running = True
        while running:
            # Gestionar eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F5:
                        self.debug_system.toggle_debug_mode()
                    if event.key == pygame.K_SPACE:
                        # Disparar una bala si el jugador tiene un cañón
                        self.player_paddle.shoot_bullet()             
                    if event.key == pygame.K_RETURN and self.game_over:
                        self.reset_game()                                   


            # Calcular delta time
            delta_time = self.clock.tick(self.fps_limit) / 1000.0

            # Actualizar el sistema de físicas
            self.control_system.update(delta_time)        

            # Actualizar el sistema de power_ups
            self.power_up_system.update(delta_time)

            # Actualizar el sistema de debug
            self.power_up_system.update(delta_time)

            self.wave_effect_system.update(delta_time)

            # Renderizar todo
            self.render()

    def render(self):
        self.screen.fill(BLACK)
        
        # Dibujar la interfaz superior
        pygame.draw.rect(self.screen, GREEN, (0, 0, WIDTH, INTERFACE_HEIGHT))

        # Dibujar la zona de juego
        pygame.draw.rect(self.screen, WHITE, (0, INTERFACE_HEIGHT, WIDTH, GAME_AREA_HEIGHT), 2)

        if not self.game_over:
            self.wave_effect_system.draw(self.screen)

            # Dibujar todas las entidades
            for entity in self.control_system.entities:
                entity.draw(self.screen)

            self.debug_system.draw(self.screen)

            
            # Mostrar el mensaje si el cañón está activo
            if self.player_paddle.has_cannon:
                font = pygame.font.SysFont('Arial', 24, bold=True)
                text_surface = font.render('¡¡¡PULSA ESPACIO!!!', True, (255, 0, 0))
                text_rect = text_surface.get_rect(center=(WIDTH // 2, INTERFACE_HEIGHT // 2))  # Centrando el texto
                self.screen.blit(text_surface, text_rect)



        # Mostrar mensaje de victoria/derrota
        if self.game_over:
            font = pygame.font.SysFont('Arial', 30, bold=True)
            message_surface = font.render(self.win_message, True, WHITE)
            message_rect = message_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            self.screen.blit(message_surface, message_rect)

            restart_font = pygame.font.SysFont('Arial', 15, bold=True)
            restart_surface = restart_font.render("Reiniciar con Enter", True, WHITE)
            restart_rect = restart_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
            self.screen.blit(restart_surface, restart_rect)


        # Actualizar la pantalla
        pygame.display.flip()

# Iniciar el juego
if __name__ == "__main__":
    game = Game()
    game.run()

    pygame.quit()
