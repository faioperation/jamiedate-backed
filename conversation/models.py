from django.db import models


class PlatformUser(models.Model):
    PLATFORM_CHOICES = [
        ("facebook", "Facebook"),
        ("instagram", "Instagram"),
        ("whatsapp", "WhatsApp"),
    ]
    STATUS_CHOICES = [
        ("coldLead", "Cold Lead"),
        ("nurture", "Nurture"),
        ("warmLead", "Warm Lead"),
        ("hotLead", "Hot Lead"),
    ]

    sender_id = models.CharField(max_length=200, unique=True, db_index=True)
    platform = models.CharField(
        max_length=20, choices=PLATFORM_CHOICES, default="facebook", db_index=True
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    profile_pic = models.URLField(max_length=500, blank=True, null=True)

    # Bot state
    current_state = models.CharField(max_length=100, default="ENTRY")
    bot_attributes = models.JSONField(default=dict, blank=True)

    # Lead / engagement tracking

    score = models.IntegerField(
        default=0, help_text="Latest progress_score from bot (0–100)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="coldLead",
        db_index=True,
        help_text="Auto-derived: coldLead<60, nurture=60-70, warmLead=70-80, hotLead≥80",
    )

    last_interaction = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-last_interaction"]
        verbose_name = "Sender"
        verbose_name_plural = "Senders"

    # ── helpers ──────────────────────────────────────────────
    @property
    def display_name(self):
        return self.name or f"User-{self.sender_id[-6:]}"

    def update_score_and_status(self, new_score):
        self.score = new_score

        if new_score >= 80:
            self.status = "hotLead"
        elif new_score >= 70:
            self.status = "warmLead"
        elif new_score >= 60:
            self.status = "nurture"
        else:
            self.status = "coldLead"

    def __str__(self):
        return f"{self.display_name} ({self.get_platform_display()}) [{self.status}]"


class Message(models.Model):
    sender = models.ForeignKey(
        PlatformUser, on_delete=models.CASCADE, related_name="messages"
    )
    message_id = models.CharField(
        max_length=255, unique=True, null=True, blank=True, db_index=True
    )
    text = models.TextField(null=True, blank=True)
    image_url = models.URLField(max_length=1000, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    is_from_bot = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["sender", "timestamp"]),
        ]

    def __str__(self):
        content = (
            (self.text[:50] + "...")
            if self.text and len(self.text) > 50
            else (self.text or "[Image]")
        )
        return f"{'Bot' if self.is_from_bot else self.sender.display_name}: {content}"
