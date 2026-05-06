import pygame

from pygame_ui import theme
from pygame_ui.scenes.scene_base import SceneBase
from pygame_ui.ui_helpers import truncate_text, wrap_text
from pygame_ui.widgets.header_panel import HeaderPanel
from pygame_ui.widgets.inc_dec_control import IncDecControl
from pygame_ui.widgets.label_value_text import LabelValueText
from pygame_ui.widgets.panel import Panel
from pygame_ui.widgets.resource_header import ResourceHeader
from pygame_ui.widgets.selection_details_panel import SelectionDetailsPanel
from pygame_ui.widgets.status_chip import StatusChip
from pygame_ui.widgets.text_block import TextBlock
from pygame_ui.widgets.row_styles import draw_selectable_row
from pygame_ui.widgets.scrollable_list_panel import ScrollableListPanel

from systems.contract_lifecycle import ensure_contract_fields, is_expiring_hero
from systems.contract_negotiation import (
    clear_offer,
    clear_renewal_offer,
    default_offer_for_hero,
    default_renewal_offer_for_hero,
    ensure_contract_state,
    estimate_player_offer_grade,
    estimate_player_renewal_grade,
    estimate_rival_grade_hint,
    get_offer_for_hero,
    get_renewal_offer_for_hero,
    queue_offer,
    queue_renewal_offer,
    renewal_ask_for_hero,
    renewal_risk_label,
    resolve_contract_round,
    rival_summary_for_hero,
    visible_offer_modifiers,
    visible_renewal_modifiers,
    market_stage_label,
)
from systems.hero_career import career_phase_name, career_phase_summary
from systems.hero_progression import ensure_progression_fields

from ..widgets.button import Button


class ManagementScene(SceneBase):
    ASK_COLUMN_X = 748
    PLAYER_GRADE_X = -238
    RIVAL_GRADE_X = -154
    QUEUE_CHIP_X = -70

    def __init__(self, state, on_return_to_hub, on_save_game):
        super().__init__()

        self.state = state
        self.on_return_to_hub = on_return_to_hub
        self.on_save_game = on_save_game

        ensure_contract_state(self.state)

        self.selected_hero = None
        self.selected_source = ""
        self.status_message = "Contract board active."

        self.offer_campaigns = 1
        self.offer_signing_fee = 25

        self.details_panel = SelectionDetailsPanel(
            rect=(40, 770, 1210, 230),
            title="Contract Negotiation Details",
            empty_message="Select a recruit or roster hero to inspect.",
            left_width=360,
            right_width=760,
        )

        self.controls_panel_rect = (1270, 770, 610, 230)

        self.recruits_panel = ScrollableListPanel(
            rect=(40, 150, 1120, 600),
            title="Available Recruits",
            row_height=82,
            row_gap=10,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )

        self.roster_panel = ScrollableListPanel(
            rect=(1200, 150, 680, 600),
            title="Roster",
            row_height=72,
            row_gap=10,
            visible_rows=None,
            font=self.font,
            title_font=self.title_font,
            padding=18,
            title_height=64,
        )

        self.campaign_control = IncDecControl(
            rect=(1310, 845, 220, 72),
            title="Campaigns",
            value_getter=lambda: str(self.offer_campaigns),
            on_decrease=self.decrease_campaigns,
            on_increase=self.increase_campaigns,
        )

        self.signing_fee_control = IncDecControl(
            rect=(1600, 845, 240, 72),
            title="Signing Fee",
            value_getter=lambda: f"{self.offer_signing_fee}g",
            on_decrease=self.decrease_fee,
            on_increase=self.increase_fee,
        )

    def roster_capacity(self):
        return self.state.guild_upgrades.roster_capacity

    def sync_lists(self):
        ensure_contract_state(self.state)

        for hero in self.state.roster:
            ensure_contract_fields(hero)
            ensure_progression_fields(hero)

        for hero in self.state.available_contracts:
            ensure_contract_fields(hero)
            ensure_progression_fields(hero)

        self.recruits_panel.set_items(self.state.available_contracts)
        self.roster_panel.set_items(self.state.roster)

        if self.selected_source == "Recruit" and self.selected_hero not in self.state.available_contracts:
            self.selected_hero = None
            self.selected_source = ""

        if self.selected_source == "Roster" and self.selected_hero not in self.state.roster:
            self.selected_hero = None
            self.selected_source = ""

    def handle_event(self, event):
        self.sync_lists()

        if self.recruits_panel.handle_event(event):
            return

        if self.roster_panel.handle_event(event):
            return

        if self.handle_buttons_click(event, self.build_all_buttons()):
            return

        if self.is_left_click(event):
            self.handle_row_click(event.pos)

    def update(self, mouse_pos):
        super().update(mouse_pos)
        self.sync_lists()
        self.recruits_panel.update(mouse_pos)
        self.roster_panel.update(mouse_pos)

    def draw(self, screen):
        self.sync_lists()
        self.clear_screen(screen)

        self.draw_header(screen)

        self.recruits_panel.draw(
            screen=screen,
            row_drawer=self.draw_recruit_row,
            selected_item=self.selected_hero if self.selected_source == "Recruit" else None,
            empty_text="No recruits available.",
        )

        self.roster_panel.draw(
            screen=screen,
            row_drawer=self.draw_roster_row,
            selected_item=self.selected_hero if self.selected_source == "Roster" else None,
            empty_text="No heroes hired yet.",
        )

        self.draw_recruit_table_headers(screen)
        self.draw_details(screen)
        self.draw_controls_panel(screen)

        self.update_and_draw_buttons(screen, self.build_all_buttons())


    def draw_header(self, screen):
        HeaderPanel(
            rect=(40, 30, 1840, 110),
            title="Guild Management",
            stats="",
            status_message=self.status_message,
            stats_pos=(70, 82),
            status_pos=(980, 122),
        ).draw(screen, self.title_font, self.header_font, self.font)

        expiring = sum(1 for hero in self.state.roster if is_expiring_hero(hero))
        renewals = len(getattr(self.state, "renewal_offers", []))
        stage_text = market_stage_label(self.state)

        ResourceHeader(
            resources=[
                ("Gold", f"{self.state.gold}g"),
                ("Roster", f"{len(self.state.roster)}/{self.roster_capacity()}"),
                ("Recruits", len(self.state.available_contracts)),
                ("Stage", stage_text),
                ("Offers", len(getattr(self.state, "contract_offers", []))),
                ("Renewals", renewals),
                ("Expiring", expiring),
            ],
            spacing=135,
            item_max_width=185,
            font_size=24,
            label_color=theme.TEXT_MUTED,
            value_color=theme.TEXT_PRIMARY,
            label_bold=False,
            value_bold=True,
        ).draw(screen, self.font, 60, 82)

    def draw_recruit_table_headers(self, screen):
        panel_x = self.recruits_panel.rect.x
        panel_y = self.recruits_panel.rect.y
        panel_w = self.recruits_panel.rect.width

        header_y = panel_y + 42

        recruit_x = panel_x + 30
        ask_x = panel_x + self.ASK_COLUMN_X + 28
        your_x = panel_x + panel_w + self.PLAYER_GRADE_X - 36
        rival_x = panel_x + panel_w + self.RIVAL_GRADE_X - 38
        queue_x = panel_x + panel_w + self.QUEUE_CHIP_X - 14

        screen.blit(
            self.small_font.render("Recruit", True, theme.TEXT_MUTED),
            (recruit_x, header_y),
        )
        screen.blit(
            self.small_font.render("Ask", True, theme.TEXT_MUTED),
            (ask_x, header_y),
        )
        screen.blit(
            self.small_font.render("Your Offer", True, theme.TEXT_MUTED),
            (your_x, header_y),
        )
        screen.blit(
            self.small_font.render("Rival Offer", True, theme.TEXT_MUTED),
            (rival_x, header_y),
        )
        screen.blit(
            self.small_font.render("Q", True, theme.TEXT_MUTED),
            (queue_x, header_y),
        )

    def draw_recruit_row(self, screen, hero, row_rect, is_selected, is_hovered):
        ensure_progression_fields(hero)

        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style="dark",
        )

        offer = get_offer_for_hero(self.state, hero)
        queued = offer is not None

        if offer is None:
            campaigns = hero.preferred_campaigns
            signing_fee = hero.asking_signing_fee
            your_offer_grade = "N/A"
        else:
            campaigns = int(offer["offered_campaigns"])
            signing_fee = int(offer["offered_signing_fee"])
            your_offer_grade = estimate_player_offer_grade(self.state, hero, campaigns, signing_fee)

        rival_hint = estimate_rival_grade_hint(self.state, hero)

        subclass = hero.primary_subclass or hero.subclass or "Base"
        phase = career_phase_name(hero)

        top_line = f"{hero.name} | {hero.hero_class}/{subclass} | {phase} | Age {hero.age}"
        screen.blit(
            self.font.render(
                truncate_text(top_line, self.font, row_rect.width - 420),
                True,
                theme.TEXT_PRIMARY,
            ),
            (row_rect.x + 14, row_rect.y + 10),
        )

        ask_text = f"{hero.asking_signing_fee}g / {hero.preferred_campaigns}c"
        screen.blit(
            self.small_font.render(ask_text, True, theme.TEXT_SECONDARY),
            (row_rect.x + self.ASK_COLUMN_X, row_rect.y + 14),
        )

        self.draw_grade_chip(
            screen,
            rect=(row_rect.right + self.PLAYER_GRADE_X, row_rect.y + 10, 72, 24),
            grade_text=your_offer_grade,
        )
        self.draw_grade_chip(
            screen,
            rect=(row_rect.right + self.RIVAL_GRADE_X, row_rect.y + 10, 72, 24),
            grade_text=rival_hint,
        )

        StatusChip(
            rect=(row_rect.right + self.QUEUE_CHIP_X, row_rect.y + 10, 56, 24),
            text="Q" if queued else "-",
            style="good" if queued else "default",
        ).draw(screen, self.small_font)

        bottom_line = (
            f"Pwr {hero.combat_power()} | "
            f"{career_phase_summary(hero)} | "
            f"Offer {signing_fee}g / {campaigns}c"
        )
        screen.blit(
            self.small_font.render(
                truncate_text(bottom_line, self.small_font, row_rect.width - 32),
                True,
                theme.TEXT_MUTED,
            ),
            (row_rect.x + 14, row_rect.y + 50),
        )

    def draw_roster_row(self, screen, hero, row_rect, is_selected, is_hovered):
        ensure_contract_fields(hero)
        ensure_progression_fields(hero)

        style = "green" if hero.injured_years_remaining <= 0 else "brown"
        if is_expiring_hero(hero):
            style = "brown"

        draw_selectable_row(
            screen=screen,
            rect=row_rect,
            is_selected=is_selected,
            is_hovered=is_hovered,
            style=style,
        )

        subclass = hero.primary_subclass or hero.subclass or "Base"
        phase = career_phase_name(hero)

        screen.blit(
            self.font.render(
                truncate_text(
                    f"{hero.name} | {hero.hero_class}/{subclass} | {phase}",
                    self.font,
                    row_rect.width - 170,
                ),
                True,
                (210, 240, 210),
            ),
            (row_rect.x + 14, row_rect.y + 10),
        )

        chip_text = f"{hero.contract_years}c left"
        chip_style = "danger" if hero.contract_years <= 1 else "info"

        StatusChip(
            rect=(row_rect.right - 122, row_rect.y + 10, 106, 24),
            text=chip_text,
            style=chip_style,
        ).draw(screen, self.small_font)

        if is_expiring_hero(hero):
            bottom_line = (
                f"Age {hero.age} | {career_phase_summary(hero)} | Renewal due"
            )
        else:
            bottom_line = (
                f"Age {hero.age} | {career_phase_summary(hero)} | "
                f"Abilities {len(hero.unlocked_abilities)} | "
                f"Satisfaction {hero.satisfaction_label()}"
            )

        screen.blit(
            self.small_font.render(
                truncate_text(bottom_line, self.small_font, row_rect.width - 28),
                True,
                (180, 210, 180),
            ),
            (row_rect.x + 14, row_rect.y + 46),
        )

    def draw_grade_chip(self, screen, rect, grade_text):
        if grade_text == "N/A":
            StatusChip(rect=rect, text="N/A", style="default").draw(screen, self.small_font)
            return

        style = self.grade_style_for_hint(grade_text)
        StatusChip(rect=rect, text=grade_text, style=style).draw(screen, self.small_font)

    def draw_details(self, screen):
        if not self.selected_hero:
            self.details_panel.draw(
                screen=screen,
                title_font=self.title_font,
                font=self.font,
                left_lines=[],
                right_lines=[],
            )
            return

        hero = self.selected_hero
        ensure_progression_fields(hero)

        if self.selected_source == "Recruit":
            self.draw_recruit_details(screen, hero)
        else:
            self.draw_roster_details(screen, hero)

    def draw_recruit_details(self, screen, hero):
        self.details_panel.details_panel.panel.draw(screen, self.title_font)

        left_x = self.details_panel.rect.x + 22
        middle_x = self.details_panel.rect.x + 320
        right_x = self.details_panel.rect.x + 730
        top_y = self.details_panel.rect.y + 42

        your_grade = estimate_player_offer_grade(
            self.state,
            hero,
            self.offer_campaigns,
            self.offer_signing_fee,
        )
        rival_hint = estimate_rival_grade_hint(self.state, hero)
        modifiers = visible_offer_modifiers(
            self.state,
            hero,
            self.offer_campaigns,
            self.offer_signing_fee,
        )
        rival_summary = rival_summary_for_hero(self.state, hero)

        subclass_text = ", ".join(hero.unlocked_subclasses) if hero.unlocked_subclasses else (hero.subclass or "None")
        ability_text = ", ".join(hero.unlocked_abilities) if hero.unlocked_abilities else (hero.special_ability or "None")

        left_entries = [
            ("Recruit", hero.name),
            ("Class", hero.hero_class),
            ("Age", hero.age),
            ("Career Phase", career_phase_name(hero)),
            ("Phase Effect", career_phase_summary(hero)),
            ("Subclass", subclass_text),
        ]

        middle_entries = [
            ("Abilities", ability_text),
            ("Asking Price", f"{hero.asking_signing_fee}g"),
            ("Preferred Campaigns", hero.preferred_campaigns),
            ("Ask / Campaign", f"{hero.asking_fee_per_campaign}g"),
            ("Draft Offer", f"{self.offer_signing_fee}g / {self.offer_campaigns}c"),
            ("Your Offer Grade", your_grade),
        ]

        right_entries = [
            ("Rival Offer Grade", rival_hint),
            ("Likely Rival", rival_summary["name"]),
            ("Rival Style", rival_summary["style"]),
            ("Rival Tagline", rival_summary["tagline"] or "No tagline"),
            ("Why They Care", rival_summary["reason"]),
            ("Modifiers", ", ".join(modifiers) if modifiers else "No major visible modifiers"),
        ]

        self.draw_text_column(screen, left_entries, left_x, top_y, 260)
        self.draw_text_column(screen, middle_entries, middle_x, top_y, 360)
        self.draw_text_column(screen, right_entries, right_x, top_y, 430)

    def draw_roster_details(self, screen, hero):
        ensure_contract_fields(hero)
        ensure_progression_fields(hero)

        if is_expiring_hero(hero):
            self.draw_roster_renewal_details(screen, hero)
            return

        subclass_text = ", ".join(hero.unlocked_subclasses) if hero.unlocked_subclasses else (hero.subclass or "None")
        ability_text = ", ".join(hero.unlocked_abilities) if hero.unlocked_abilities else (hero.special_ability or "None")

        left_lines = [
            f"Hero: {hero.name}",
            f"Class: {hero.hero_class}",
            f"Age: {hero.age}",
            f"Career Phase: {career_phase_name(hero)}",
            f"Phase Effect: {career_phase_summary(hero)}",
            f"Subclasses: {subclass_text}",
        ]

        right_lines = [
            f"Abilities: {ability_text}",
            f"Power: {hero.combat_power()}",
            f"Mentorship: {hero.mentorship_value()}",
            f"Satisfaction: {hero.satisfaction}/100 ({hero.satisfaction_label()})",
            f"Retire Risk: {hero.retirement_chance() * 100:.1f}%",
            f"Contract Remaining: {hero.contract_years} campaign(s)",
        ]

        self.details_panel.draw(
            screen=screen,
            title_font=self.title_font,
            font=self.font,
            left_lines=left_lines,
            right_lines=right_lines,
        )

    def draw_roster_renewal_details(self, screen, hero):
        self.details_panel.details_panel.panel.draw(screen, self.title_font)

        left_x = self.details_panel.rect.x + 22
        middle_x = self.details_panel.rect.x + 320
        right_x = self.details_panel.rect.x + 730
        top_y = self.details_panel.rect.y + 42

        ask_campaigns, ask_fee = renewal_ask_for_hero(self.state, hero)
        renewal_grade = estimate_player_renewal_grade(
            self.state,
            hero,
            self.offer_campaigns,
            self.offer_signing_fee,
        )
        modifiers = visible_renewal_modifiers(
            self.state,
            hero,
            self.offer_campaigns,
            self.offer_signing_fee,
        )
        risk_label = renewal_risk_label(
            self.state,
            hero,
            self.offer_campaigns,
            self.offer_signing_fee,
        )

        subclass_text = ", ".join(hero.unlocked_subclasses) if hero.unlocked_subclasses else (hero.subclass or "None")
        ability_text = ", ".join(hero.unlocked_abilities) if hero.unlocked_abilities else (hero.special_ability or "None")

        left_entries = [
            ("Hero", hero.name),
            ("Renewal State", "Expiring"),
            ("Class", hero.hero_class),
            ("Age", hero.age),
            ("Career Phase", career_phase_name(hero)),
            ("Phase Effect", career_phase_summary(hero)),
        ]

        middle_entries = [
            ("Subclass", subclass_text),
            ("Abilities", ability_text),
            ("Satisfaction", f"{hero.satisfaction}/100 ({hero.satisfaction_label()})"),
            ("Renewal Ask", f"{ask_fee}g / {ask_campaigns}c"),
            ("Draft Renewal", f"{self.offer_signing_fee}g / {self.offer_campaigns}c"),
            ("Renewal Grade", renewal_grade),
        ]

        right_entries = [
            ("Renewal Risk", risk_label),
            ("Contract Remaining", f"{hero.contract_years} campaign(s)"),
            ("Modifiers", ", ".join(modifiers) if modifiers else "No major visible modifiers"),
            ("Queue Rules", "Queued renewals resolve when the current contract expires."),
            ("Failure Result", "No accepted renewal means the hero returns to the recruit market."),
        ]

        self.draw_text_column(screen, left_entries, left_x, top_y, 260)
        self.draw_text_column(screen, middle_entries, middle_x, top_y, 360)
        self.draw_text_column(screen, right_entries, right_x, top_y, 430)

    def draw_text_column(self, screen, entries, x, y, max_width):
        current_y = y
        row_gap = 10

        for entry in entries:
            if isinstance(entry, tuple) and len(entry) == 2:
                label, value = entry
                used_height = LabelValueText(
                    label=label,
                    value=value,
                    label_color=theme.TEXT_SECONDARY,
                    value_color=theme.TEXT_PRIMARY,
                    label_bold=True,
                    value_bold=False,
                    font_size=22,
                    line_spacing=2,
                    wrap_value=True,
                ).draw(
                    screen=screen,
                    font=self.font,
                    x=x,
                    y=current_y,
                    max_width=max_width,
                )
                current_y += used_height + row_gap
                continue

            wrapped = wrap_text(str(entry), self.font, max_width)
            for line in wrapped:
                screen.blit(
                    self.font.render(line, True, theme.TEXT_SECONDARY),
                    (x, current_y),
                )
                current_y += self.font.get_height() + 2

            current_y += row_gap

    def draw_controls_panel(self, screen):
        title = "Offer Controls" if self.selected_source == "Recruit" else "Actions"
        if self.selected_source == "Roster" and self.selected_hero is not None and is_expiring_hero(self.selected_hero):
            title = "Renewal Controls"
        if getattr(self.state, "market_fallback_open", False):
            title = "Fallback Hiring"

        Panel(self.controls_panel_rect, title).draw(screen, self.title_font)

        if getattr(self.state, "market_fallback_open", False):
            hint = self.small_font.render(
                "Fallback market: fixed 1-campaign prices. Hire immediately.",
                True,
                theme.TEXT_MUTED,
            )
            screen.blit(hint, (1295, 812))

            if self.selected_hero is not None and self.selected_source == "Recruit":
                price_text = self.small_font.render(
                    f"Selected price: {int(getattr(self.selected_hero, 'asking_signing_fee', 25))}g / 1c",
                    True,
                    theme.TEXT_SECONDARY,
                )
                screen.blit(price_text, (1295, 846))

            return

        if self.selected_source == "Recruit" and self.selected_hero is not None:
            hint = self.small_font.render(
                "Adjust terms, then queue the offer for this stage.",
                True,
                theme.TEXT_MUTED,
            )
            screen.blit(hint, (1295, 812))
            self.campaign_control.draw(screen, self.small_font, self.font)
            self.signing_fee_control.draw(screen, self.small_font, self.font)

        elif self.selected_source == "Roster" and self.selected_hero is not None and is_expiring_hero(self.selected_hero):
            hint = self.small_font.render(
                "Adjust renewal terms before the contract expires.",
                True,
                theme.TEXT_MUTED,
            )
            screen.blit(hint, (1295, 812))
            self.campaign_control.draw(screen, self.small_font, self.font)
            self.signing_fee_control.draw(screen, self.small_font, self.font)

        elif self.selected_source == "Roster" and self.selected_hero is not None:
            hint = self.small_font.render(
                "Roster actions for the selected hero.",
                True,
                theme.TEXT_MUTED,
            )
            screen.blit(hint, (1295, 850))

        else:
            hint = self.small_font.render(
                "Select a recruit or expiring hero to edit terms.",
                True,
                theme.TEXT_MUTED,
            )
            screen.blit(hint, (1295, 850))

    def hire_selected_fallback_hero(self):
        if self.selected_hero is None or self.selected_source != "Recruit":
            self.status_message = "Select a fallback recruit first."
            return

        if not getattr(self.state, "market_fallback_open", False):
            self.status_message = "Fallback hiring is not active."
            return

        hero = self.selected_hero
        price = int(getattr(hero, "asking_signing_fee", 25))

        if len(self.state.roster) >= self.roster_capacity():
            self.status_message = "No roster space remains."
            return

        if self.state.gold < price:
            self.status_message = f"Not enough gold to hire {hero.name}."
            return

        if hero not in self.state.available_contracts:
            self.status_message = "That recruit is no longer available."
            self.selected_hero = None
            self.selected_source = ""
            return

        self.state.gold -= price
        hero.contract_years = 1
        hero.signing_bonus = price

        self.state.roster.append(hero)
        self.state.available_contracts.remove(hero)

        if hero in getattr(self.state, "seasonal_contract_pool", []):
            self.state.seasonal_contract_pool.remove(hero)

        self.selected_hero = None
        self.selected_source = ""
        self.sync_lists()

        if self.on_save_game:
            self.on_save_game()

        self.status_message = f"Hired {hero.name} on a 1-campaign fallback deal for {price}g."

    def build_all_buttons(self):
        buttons = [
            Button((1680, 72, 140, 36), "Hub", self.on_return_to_hub),
        ]

        if not getattr(self.state, "market_fallback_open", False):
            buttons.append(Button((1490, 72, 170, 36), "Resolve Round", self.resolve_offers))

        if getattr(self.state, "market_fallback_open", False):
            if self.selected_source == "Recruit" and self.selected_hero is not None:
                buttons.append(Button((1450, 930, 170, 42), "Hire", self.hire_selected_fallback_hero))
            return buttons

        if self.selected_source == "Recruit" and self.selected_hero is not None:
            buttons.extend(self.campaign_control.get_buttons())
            buttons.extend(self.signing_fee_control.get_buttons())
            buttons.extend(
                [
                    Button((1360, 930, 130, 42), "Queue", self.queue_selected_offer),
                    Button((1510, 930, 130, 42), "Clear", self.clear_selected_offer),
                ]
            )

        if self.selected_source == "Roster" and self.selected_hero is not None and is_expiring_hero(self.selected_hero):
            buttons.extend(self.campaign_control.get_buttons())
            buttons.extend(self.signing_fee_control.get_buttons())
            buttons.extend(
                [
                    Button((1360, 930, 150, 42), "Queue Renewal", self.queue_selected_renewal),
                    Button((1530, 930, 150, 42), "Clear Renewal", self.clear_selected_renewal),
                ]
            )

        elif self.selected_source == "Roster" and self.selected_hero is not None:
            buttons.append(Button((1665, 930, 170, 42), "Release Hero", self.release_selected_hero))

        return buttons

    def handle_row_click(self, pos):
        recruit = self.recruits_panel.item_at_pos(pos)
        if recruit is not None:
            self.selected_hero = recruit
            self.selected_source = "Recruit"
            self.load_offer_editor_for_selected()
            self.status_message = f"Selected recruit: {recruit.name}"
            return

        roster_hero = self.roster_panel.item_at_pos(pos)
        if roster_hero is not None:
            self.selected_hero = roster_hero
            self.selected_source = "Roster"
            self.load_offer_editor_for_selected()
            self.status_message = f"Selected roster hero: {roster_hero.name}"

    def load_offer_editor_for_selected(self):
        if self.selected_hero is None:
            return

        if self.selected_source == "Recruit":
            offer = get_offer_for_hero(self.state, self.selected_hero)
            if offer is None:
                offer = default_offer_for_hero(self.selected_hero)

            if getattr(self.state, "market_fallback_open", False):
                self.offer_campaigns = 1
                self.offer_signing_fee = int(getattr(self.selected_hero, "asking_signing_fee", 25))
                return

            self.offer_campaigns = int(offer["offered_campaigns"])
            self.offer_signing_fee = int(offer["offered_signing_fee"])
            return

        if self.selected_source == "Roster" and is_expiring_hero(self.selected_hero):
            offer = get_renewal_offer_for_hero(self.state, self.selected_hero)
            if offer is None:
                offer = default_renewal_offer_for_hero(self.state, self.selected_hero)

            self.offer_campaigns = int(offer["offered_campaigns"])
            self.offer_signing_fee = int(offer["offered_signing_fee"])

    def decrease_campaigns(self):
        if getattr(self.state, "market_fallback_open", False):
            self.offer_campaigns = 1
            return
        self.offer_campaigns = max(1, self.offer_campaigns - 1)

    def increase_campaigns(self):
        if getattr(self.state, "market_fallback_open", False):
            self.offer_campaigns = 1
            return
        self.offer_campaigns += 1

    def decrease_fee(self):
        if getattr(self.state, "market_fallback_open", False):
            if self.selected_hero is not None:
                self.offer_signing_fee = int(getattr(self.selected_hero, "asking_signing_fee", 25))
            return
        self.offer_signing_fee = max(25, self.offer_signing_fee - 25)

    def increase_fee(self):
        if getattr(self.state, "market_fallback_open", False):
            if self.selected_hero is not None:
                self.offer_signing_fee = int(getattr(self.selected_hero, "asking_signing_fee", 25))
            return
        self.offer_signing_fee += 25

    def queue_selected_offer(self):
        if self.selected_hero is None or self.selected_source != "Recruit":
            self.status_message = "Select a recruit first."
            return

        queue_offer(
            self.state,
            self.selected_hero,
            self.offer_campaigns,
            self.offer_signing_fee,
        )

        self.load_offer_editor_for_selected()

        if self.on_save_game:
            self.on_save_game()

        if getattr(self.state, "market_fallback_open", False):
            self.status_message = (
                f"Queued fallback hire for {self.selected_hero.name}: "
                f"{self.offer_signing_fee}g / 1c."
            )
        else:
            self.status_message = (
                f"Queued offer for {self.selected_hero.name}: "
                f"{self.offer_signing_fee}g / {self.offer_campaigns}c."
            )

    def clear_selected_offer(self):
        if self.selected_hero is None or self.selected_source != "Recruit":
            self.status_message = "Select a recruit first."
            return

        clear_offer(self.state, self.selected_hero)
        self.load_offer_editor_for_selected()

        if self.on_save_game:
            self.on_save_game()

        self.status_message = f"Cleared offer for {self.selected_hero.name}."

    def queue_selected_renewal(self):
        if self.selected_hero is None or self.selected_source != "Roster" or not is_expiring_hero(self.selected_hero):
            self.status_message = "Select an expiring hero first."
            return

        queue_renewal_offer(
            self.state,
            self.selected_hero,
            self.offer_campaigns,
            self.offer_signing_fee,
        )

        if self.on_save_game:
            self.on_save_game()

        self.status_message = (
            f"Queued renewal for {self.selected_hero.name}: "
            f"{self.offer_signing_fee}g / {self.offer_campaigns}c."
        )

    def clear_selected_renewal(self):
        if self.selected_hero is None or self.selected_source != "Roster" or not is_expiring_hero(self.selected_hero):
            self.status_message = "Select an expiring hero first."
            return

        clear_renewal_offer(self.state, self.selected_hero)
        self.load_offer_editor_for_selected()

        if self.on_save_game:
            self.on_save_game()

        self.status_message = f"Cleared renewal for {self.selected_hero.name}."

    def resolve_offers(self):
        messages = resolve_contract_round(self.state)

        self.sync_lists()
        self.selected_hero = None
        self.selected_source = ""

        if self.on_save_game:
            self.on_save_game()

        self.status_message = messages[-1] if messages else "Contract round resolved."

    def release_selected_hero(self):
        hero = self.selected_hero
        if hero is None or self.selected_source != "Roster":
            return

        if hero in self.state.roster:
            self.state.roster.remove(hero)
            self.status_message = f"Released {hero.name} from the guild."
            self.selected_hero = None
            self.selected_source = ""

            if self.on_save_game:
                self.on_save_game()

    def grade_style_for_hint(self, grade_text: str) -> str:
        if grade_text.startswith("A"):
            return "good"
        if grade_text.startswith("B"):
            return "info"
        if grade_text.startswith("C"):
            return "warning"
        if grade_text.startswith("D") or grade_text.startswith("F"):
            return "danger"
        return "default"

    def satisfaction_style(self, hero) -> str:
        if hero.satisfaction >= 75:
            return "good"
        if hero.satisfaction >= 45:
            return "warning"
        return "danger"