from core.validation import Schema, fields, validators


class PlantSchema(Schema):
    """
    Validation Schema for Plant Payload (Admin Panel Input).
    Conforms to PlantSchema Contract v1.0 (Stage 3.1).
    """

    # --- Required Fields ---
    category_id = fields.Integer(
        required=True,
        validators=[
            validators.GreaterThan(0, error_message="category_id_must_be_positive")
        ],
    )

    name = fields.String(
        required=True,
        validators=[
            validators.Length(min=1, max=150, error_message="name_length_invalid")
        ],
    )

    # Migration Decision: Normalized to Number (Float/Int) & required=True per HTML form contract
    price = fields.Number(
        required=True,
        validators=[validators.GreaterThan(0, error_message="price_must_be_positive")],
    )

    # --- Optional / Numeric Fields ---
    promotion_percent = fields.Integer(
        required=False,
        default=0,
        validators=[
            validators.Range(
                min_val=0, max_val=100, error_message="promotion_percent_out_of_range"
            )
        ],
    )

    # --- Optional / Text Fields ---
    promotion_message = fields.String(required=False, default="")
    description = fields.String(required=False, default="")

    # --- Characteristics (Optional, Max 150 chars) ---
    light = fields.String(
        required=False,
        default="",
        validators=[
            validators.Length(max=150, error_message="light_max_length_exceeded")
        ],
    )

    evergreen = fields.String(
        required=False,
        default="",
        validators=[
            validators.Length(max=150, error_message="evergreen_max_length_exceeded")
        ],
    )

    maintenance = fields.String(
        required=False,
        default="",
        validators=[
            validators.Length(max=150, error_message="maintenance_max_length_exceeded")
        ],
    )

    height = fields.String(
        required=False,
        default="",
        validators=[
            validators.Length(max=150, error_message="height_max_length_exceeded")
        ],
    )

    # --- App Context / Language ---
    lang = fields.String(
        required=False,
        default="ru",
        validators=[
            validators.Choice(["ru", "en", "ro"], error_message="unsupported_language")
        ],
    )
