import sys
from time import sleep
import pygame
from settings import Settings
from ship import Ship
from bullet import Bullet
from alien import Alien
from button import Button
from scoreboard import Scoreboard
from game_stats import GameStats


class AlienInvasion:
    """Overall class to manage game assets and behavior."""

    def __init__(self):
        """Initialize the game, and create game resources."""
        pygame.init()
        self.settings = Settings()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.settings.screen_width = self.screen.get_rect().width
        self.settings.screen_height = self.screen.get_rect().height
        pygame.display.set_caption("Alien Invasion")
        self.bg_color = self.settings.bg_color
        self.stats = GameStats(self)

        # Initialize game object attributes.
        self.ship = Ship(self)
        self.bullets = pygame.sprite.Group()
        self.aliens = pygame.sprite.Group()
        self._create_fleet()

        # Initialize button attributes.
        self.play_button = Button(self, "Play")
        self.replay_button = Button(self, "Replay")
        self.warning_button = Button(self, "You lost a ship!")

        # Initialize scoreboard and level attributes.
        self.scoreboard = Scoreboard(self)

        # Load music.
        pygame.mixer.music.load('music/background_music.wav')
        self.shooting_sound = pygame.mixer.Sound('music/shooting_sound.wav')
        self.explosion_sound = pygame.mixer.Sound('music/explosion_sound.wav')
        self.failure_sound = pygame.mixer.Sound('music/failure_sound.wav')
        self.level_up_sound = pygame.mixer.Sound('music/level_up_sound.wav')

        # Initialize history high score.
        with open('my_highest_score.txt') as file_object:
            self.history_high_score = int(file_object.read())

    def run_game(self):
        """Start the main loop for the game."""
        # Initialize background music.
        pygame.mixer.music.play(-1)

        while True:
            self._check_events()

            if self.stats.game_active:
                self.ship.update()
                self._update_bullets()
                self._update_aliens()

            self._update_screen()

    def _check_events(self):
        """Respond to key presses and mouse events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                self._check_keydown_events(event)
            elif event.type == pygame.KEYUP:
                self._check_keyup_events(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                self._check_mousedown_events(mouse_pos)

    def _check_keydown_events(self, event):
        """Respond to key presses."""
        if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
            self.ship.moving_right = True
        elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
            self.ship.moving_left = True
        elif event.key == pygame.K_ESCAPE:
            sys.exit()
        elif event.key == pygame.K_SPACE:
            self._fire_bullet()
        elif event.key == pygame.K_c:
            print(f"The number of aliens: {len(self.aliens)}")
            print(f"The number of bullets: {len(self.bullets)}")
        elif event.key == pygame.K_p:
            if self.stats.game_active:
                self.stats.game_active = False
                pygame.mixer.music.pause()
            else:
                self.stats.game_active = True
                pygame.mixer.music.unpause()

    def _check_keyup_events(self, event):
        """Respond to key releases."""
        if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
            self.ship.moving_right = False
        elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
            self.ship.moving_left = False

    def _check_mousedown_events(self, mouse_pos):
        """Respond to mouse presses."""
        button_clicked = self.play_button.rect.collidepoint(mouse_pos) or \
                         self.replay_button.rect.collidepoint(mouse_pos)
        if button_clicked and not self.stats.game_active:
            self.stats.reset_stats()
            self.scoreboard.prep_score()
            self.scoreboard.prep_level()
            self.scoreboard.prep_ship()
            self.settings.initialize_dynamic_settings()
            self.stats.game_active = True
            pygame.mouse.set_visible(False)

    def _fire_bullet(self):
        """Create a new bullet and add it to the bullets group."""
        if len(self.bullets) < self.settings.bullet_allowed:
            new_bullet = Bullet(self)
            self.shooting_sound.play()
            self.bullets.add(new_bullet)

    def _update_bullets(self):
        """Update positions of bullets and get rid of old bullets."""
        self.bullets.update()
        # Get rid of bullets that have disappeared.
        for bullet in self.bullets.sprites():
            if bullet.rect.bottom <= 0:
                self.bullets.remove(bullet)

        self._check_bullet_alien_collisions()

    def _check_bullet_alien_collisions(self):
        """Respond to bullet-alien collisions."""
        # Remove any bullets and aliens that have collided.
        collisions = pygame.sprite.groupcollide(self.bullets, self.aliens, True, True)
        if collisions:
            for aliens in collisions.values():
                self.stats.score += self.settings.alien_points * len(aliens)
            self.explosion_sound.play()
            self.scoreboard.prep_score()
        if not self.aliens:
            # Destroy existing bullets and create new fleet.
            self.bullets.empty()
            self._create_fleet()
            self.settings.increase_value()
            self.stats.level += 1
            self.level_up_sound.play()
            self.scoreboard.prep_level()

    def _create_fleet(self):
        """Create the fleet of aliens."""
        # Make an alien.
        alien = Alien(self)
        alien_width, alien_height = alien.rect.size
        available_space_x = self.settings.screen_width - (2 * alien_width)
        number_alien_x = available_space_x // (2 * alien_width)

        # Determine the number of rows of aliens that fit on the screen.
        ship_height = self.ship.rect.height
        available_space_y = self.settings.screen_height - (3 * alien_height) - ship_height
        number_alien_y = available_space_y // (2 * alien_height)

        # Create the full fleet of aliens.
        for row_number in range(number_alien_y):
            for alien_number in range(number_alien_x):
                self._create_alien(alien_number, row_number)

    def _create_alien(self, alien_number, row_number):
        """Create an alien and place it in the row."""
        alien = Alien(self)
        alien_width, alien_height = alien.rect.size
        alien.x = alien_width + 2 * alien_width * alien_number
        alien.rect.x = alien.x
        alien.rect.y = alien_height + 2 * alien_height * row_number
        self.aliens.add(alien)

    def _update_aliens(self):
        """Check if the fleet is at an edge, then update the positions of all aliens in the fleet."""
        self._check_fleet_edges()
        self.aliens.update()

        # Look for alien-ship collisions.
        if pygame.sprite.spritecollideany(self.ship, self.aliens):
            self._ship_hit()

        # Look for aliens hitting the bottom of the screen.
        self._check_aliens_bottom()

    def _check_aliens_bottom(self):
        """Check if any aliens have reached the bottom of the screen."""
        screen_rect = self.screen.get_rect()
        for alien in self.aliens.sprites():
            if alien.rect.bottom >= screen_rect.bottom:
                # Treat this the same as if the ship got hit.
                self._ship_hit()
                break

    def _ship_hit(self):
        """Respond to the ship being hit by an alien."""
        self.scoreboard.check_high_score()
        self.failure_sound.play()

        if self.stats.ship_left > 0:
            # Decrement ships left
            self.stats.ship_left -= 1
            self.scoreboard.prep_ship()

            # Get rid of any remaining aliens and bullets.
            self.aliens.empty()
            self.bullets.empty()

            # Create a new fleet.
            self._create_fleet()
            self.ship.center_ship()

            # Warning.
            while sleep(0.5):
                self.warning_button.button_color = (255, 0, 0)
                self.warning_button.draw_button()

        else:
            self.stats.game_active = False
            pygame.mouse.set_visible(True)

    def _check_fleet_edges(self):
        """Respond appropriately if any aliens have reached an edge."""
        for alien in self.aliens.sprites():
            if alien.check_edges():
                self._change_fleet_direction()
                break

    def _change_fleet_direction(self):
        """Drop the entire fleet and change the fleet's direction."""
        for alien in self.aliens.sprites():
            alien.rect.y += self.settings.fleet_drop_speed
        self.settings.fleet_direction *= -1

    def _update_screen(self):
        """Update images on the screen, and flip to the new screen."""
        self.screen.fill(self.bg_color)
        self.ship.blitme()
        for bullet in self.bullets.sprites():
            bullet.draw_bullet()
        self.aliens.draw(self.screen)
        self.scoreboard.show_score()
        if not self.stats.game_active:
            if self.stats.ship_left > 0:
                self.play_button.draw_button()
            else:
                self.replay_button.draw_button()
        pygame.display.flip()


if __name__ == '__main__':
    # Make a game instance, and run the game.
    ai = AlienInvasion()
    ai.run_game()
