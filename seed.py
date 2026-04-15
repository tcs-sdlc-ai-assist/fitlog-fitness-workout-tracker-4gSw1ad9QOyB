import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import SessionLocal, engine, Base
from models.user import User
from models.exercise import Exercise
from models.workout_template import WorkoutTemplate
from models.template_exercise import TemplateExercise
from utils.security import hash_password


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        _seed_admin(db)
        _seed_exercises(db)
        _seed_system_templates(db)
        db.commit()
        print("Database seeded successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


def _seed_admin(db):
    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        print("Admin user already exists, skipping.")
        return

    admin = User(
        username="admin",
        email="admin@fitlog.com",
        display_name="Admin",
        password_hash=hash_password("admin123"),
        role="admin",
    )
    db.add(admin)
    db.flush()
    print("Admin user created (admin / admin123).")


def _seed_exercises(db):
    existing_count = db.query(Exercise).filter(Exercise.is_system == True).count()
    if existing_count >= 30:
        print(f"Exercises already seeded ({existing_count} found), skipping.")
        return

    exercises = [
        # Chest (6)
        {
            "name": "Barbell Bench Press",
            "muscle_group": "chest",
            "equipment": "barbell",
            "instructions": "Lie on a flat bench, grip the barbell slightly wider than shoulder-width. Lower the bar to your mid-chest, then press it back up to full arm extension.",
        },
        {
            "name": "Incline Dumbbell Press",
            "muscle_group": "chest",
            "equipment": "dumbbell",
            "instructions": "Set an adjustable bench to 30-45 degrees. Press dumbbells from shoulder level to full extension above your upper chest.",
        },
        {
            "name": "Dumbbell Flyes",
            "muscle_group": "chest",
            "equipment": "dumbbell",
            "instructions": "Lie on a flat bench with dumbbells extended above your chest. Lower the weights in a wide arc until you feel a stretch, then squeeze them back together.",
        },
        {
            "name": "Cable Crossover",
            "muscle_group": "chest",
            "equipment": "cable",
            "instructions": "Stand between two cable stations with handles set high. Pull the handles down and together in front of your chest in a hugging motion.",
        },
        {
            "name": "Push-Up",
            "muscle_group": "chest",
            "equipment": "bodyweight",
            "instructions": "Start in a plank position with hands slightly wider than shoulder-width. Lower your body until your chest nearly touches the floor, then push back up.",
        },
        {
            "name": "Decline Bench Press",
            "muscle_group": "chest",
            "equipment": "barbell",
            "instructions": "Lie on a decline bench, grip the barbell at shoulder width. Lower the bar to your lower chest, then press it back up.",
        },
        # Back (6)
        {
            "name": "Barbell Deadlift",
            "muscle_group": "back",
            "equipment": "barbell",
            "instructions": "Stand with feet hip-width apart, grip the bar just outside your knees. Drive through your heels, extending hips and knees simultaneously to stand up.",
        },
        {
            "name": "Pull-Up",
            "muscle_group": "back",
            "equipment": "bodyweight",
            "instructions": "Hang from a bar with an overhand grip slightly wider than shoulder-width. Pull yourself up until your chin clears the bar, then lower with control.",
        },
        {
            "name": "Barbell Bent-Over Row",
            "muscle_group": "back",
            "equipment": "barbell",
            "instructions": "Hinge at the hips with a slight knee bend, grip the barbell. Pull the bar to your lower chest, squeezing your shoulder blades together.",
        },
        {
            "name": "Seated Cable Row",
            "muscle_group": "back",
            "equipment": "cable",
            "instructions": "Sit at a cable row station with feet on the platform. Pull the handle to your lower chest, keeping your back straight and squeezing your shoulder blades.",
        },
        {
            "name": "Lat Pulldown",
            "muscle_group": "back",
            "equipment": "cable",
            "instructions": "Sit at a lat pulldown machine, grip the bar wider than shoulder-width. Pull the bar down to your upper chest, then slowly return to the start.",
        },
        {
            "name": "Dumbbell Single-Arm Row",
            "muscle_group": "back",
            "equipment": "dumbbell",
            "instructions": "Place one knee and hand on a bench. With the other hand, row a dumbbell to your hip, keeping your elbow close to your body.",
        },
        # Shoulders (5)
        {
            "name": "Overhead Press",
            "muscle_group": "shoulders",
            "equipment": "barbell",
            "instructions": "Stand with feet shoulder-width apart, grip the barbell at shoulder height. Press the bar overhead to full arm extension, then lower back to shoulders.",
        },
        {
            "name": "Dumbbell Lateral Raise",
            "muscle_group": "shoulders",
            "equipment": "dumbbell",
            "instructions": "Stand with dumbbells at your sides. Raise your arms out to the sides until they are parallel to the floor, then lower with control.",
        },
        {
            "name": "Face Pull",
            "muscle_group": "shoulders",
            "equipment": "cable",
            "instructions": "Set a cable with rope attachment at upper chest height. Pull the rope towards your face, separating the ends and squeezing your rear delts.",
        },
        {
            "name": "Arnold Press",
            "muscle_group": "shoulders",
            "equipment": "dumbbell",
            "instructions": "Start with dumbbells in front of your shoulders, palms facing you. Rotate your palms outward as you press the weights overhead.",
        },
        {
            "name": "Dumbbell Front Raise",
            "muscle_group": "shoulders",
            "equipment": "dumbbell",
            "instructions": "Stand with dumbbells in front of your thighs. Raise one or both arms straight in front of you to shoulder height, then lower slowly.",
        },
        # Arms (Biceps + Triceps) (6)
        {
            "name": "Barbell Curl",
            "muscle_group": "biceps",
            "equipment": "barbell",
            "instructions": "Stand with an underhand grip on the barbell, arms extended. Curl the bar up to shoulder level, keeping your elbows pinned to your sides.",
        },
        {
            "name": "Dumbbell Hammer Curl",
            "muscle_group": "biceps",
            "equipment": "dumbbell",
            "instructions": "Stand with dumbbells at your sides, palms facing each other. Curl the weights up without rotating your wrists, then lower with control.",
        },
        {
            "name": "Concentration Curl",
            "muscle_group": "biceps",
            "equipment": "dumbbell",
            "instructions": "Sit on a bench, brace your elbow against your inner thigh. Curl the dumbbell up, squeezing your bicep at the top, then lower slowly.",
        },
        {
            "name": "Tricep Pushdown",
            "muscle_group": "triceps",
            "equipment": "cable",
            "instructions": "Stand at a cable station with a straight or V-bar attachment. Push the bar down until your arms are fully extended, keeping elbows at your sides.",
        },
        {
            "name": "Skull Crusher",
            "muscle_group": "triceps",
            "equipment": "barbell",
            "instructions": "Lie on a flat bench holding an EZ-bar with arms extended above your chest. Lower the bar towards your forehead by bending at the elbows, then extend back up.",
        },
        {
            "name": "Overhead Tricep Extension",
            "muscle_group": "triceps",
            "equipment": "dumbbell",
            "instructions": "Hold a dumbbell with both hands overhead. Lower it behind your head by bending at the elbows, then press it back up to full extension.",
        },
        # Legs (6)
        {
            "name": "Barbell Back Squat",
            "muscle_group": "legs",
            "equipment": "barbell",
            "instructions": "Place the barbell on your upper back. Squat down by bending your knees and hips until your thighs are parallel to the floor, then stand back up.",
        },
        {
            "name": "Romanian Deadlift",
            "muscle_group": "legs",
            "equipment": "barbell",
            "instructions": "Hold a barbell at hip level. Hinge at the hips, lowering the bar along your legs while keeping a slight knee bend. Return to standing by driving your hips forward.",
        },
        {
            "name": "Leg Press",
            "muscle_group": "legs",
            "equipment": "machine",
            "instructions": "Sit in the leg press machine with feet shoulder-width apart on the platform. Lower the weight by bending your knees, then press back to the start.",
        },
        {
            "name": "Walking Lunge",
            "muscle_group": "legs",
            "equipment": "dumbbell",
            "instructions": "Hold dumbbells at your sides. Step forward into a lunge, lowering your back knee towards the floor. Push off your front foot and step into the next lunge.",
        },
        {
            "name": "Leg Curl",
            "muscle_group": "legs",
            "equipment": "machine",
            "instructions": "Lie face down on a leg curl machine. Curl the weight up by bending your knees, squeezing your hamstrings at the top, then lower with control.",
        },
        {
            "name": "Calf Raise",
            "muscle_group": "legs",
            "equipment": "machine",
            "instructions": "Stand on a calf raise machine with the balls of your feet on the platform. Rise up onto your toes, pause at the top, then lower your heels below the platform.",
        },
        # Core (5)
        {
            "name": "Plank",
            "muscle_group": "core",
            "equipment": "bodyweight",
            "instructions": "Hold a push-up position on your forearms. Keep your body in a straight line from head to heels, engaging your core throughout.",
        },
        {
            "name": "Cable Woodchop",
            "muscle_group": "core",
            "equipment": "cable",
            "instructions": "Set a cable at high position. Stand sideways to the machine and pull the handle diagonally across your body from high to low, rotating your torso.",
        },
        {
            "name": "Hanging Leg Raise",
            "muscle_group": "core",
            "equipment": "bodyweight",
            "instructions": "Hang from a pull-up bar with arms extended. Raise your legs until they are parallel to the floor, then lower them with control.",
        },
        {
            "name": "Ab Wheel Rollout",
            "muscle_group": "core",
            "equipment": "other",
            "instructions": "Kneel on the floor holding an ab wheel. Roll the wheel forward, extending your body as far as you can while maintaining a tight core, then roll back.",
        },
        {
            "name": "Russian Twist",
            "muscle_group": "core",
            "equipment": "bodyweight",
            "instructions": "Sit on the floor with knees bent and feet slightly elevated. Lean back slightly and rotate your torso side to side, optionally holding a weight.",
        },
    ]

    existing_names = {e.name for e in db.query(Exercise.name).filter(Exercise.is_system == True).all()}

    added = 0
    for ex_data in exercises:
        if ex_data["name"] in existing_names:
            continue
        exercise = Exercise(
            name=ex_data["name"],
            muscle_group=ex_data["muscle_group"],
            equipment=ex_data.get("equipment"),
            instructions=ex_data.get("instructions"),
            is_system=True,
        )
        db.add(exercise)
        added += 1

    db.flush()
    print(f"Exercises seeded: {added} added, {len(existing_names)} already existed.")


def _seed_system_templates(db):
    existing_count = db.query(WorkoutTemplate).filter(WorkoutTemplate.is_system == True).count()
    if existing_count >= 6:
        print(f"System templates already seeded ({existing_count} found), skipping.")
        return

    exercise_map = {}
    all_exercises = db.query(Exercise).filter(Exercise.is_system == True).all()
    for ex in all_exercises:
        exercise_map[ex.name] = ex.id

    def _get_id(name):
        eid = exercise_map.get(name)
        if eid is None:
            print(f"  WARNING: Exercise '{name}' not found, skipping in template.")
        return eid

    templates_data = [
        {
            "name": "Push Day",
            "description": "Chest, shoulders, and triceps focused workout.",
            "exercises": [
                {"name": "Barbell Bench Press", "sets": 4, "reps": 8, "weight": None},
                {"name": "Incline Dumbbell Press", "sets": 3, "reps": 10, "weight": None},
                {"name": "Dumbbell Flyes", "sets": 3, "reps": 12, "weight": None},
                {"name": "Overhead Press", "sets": 3, "reps": 8, "weight": None},
                {"name": "Dumbbell Lateral Raise", "sets": 3, "reps": 15, "weight": None},
                {"name": "Tricep Pushdown", "sets": 3, "reps": 12, "weight": None},
                {"name": "Overhead Tricep Extension", "sets": 3, "reps": 12, "weight": None},
            ],
        },
        {
            "name": "Pull Day",
            "description": "Back and biceps focused workout.",
            "exercises": [
                {"name": "Barbell Deadlift", "sets": 4, "reps": 5, "weight": None},
                {"name": "Pull-Up", "sets": 3, "reps": 8, "weight": None},
                {"name": "Barbell Bent-Over Row", "sets": 3, "reps": 8, "weight": None},
                {"name": "Seated Cable Row", "sets": 3, "reps": 10, "weight": None},
                {"name": "Face Pull", "sets": 3, "reps": 15, "weight": None},
                {"name": "Barbell Curl", "sets": 3, "reps": 10, "weight": None},
                {"name": "Dumbbell Hammer Curl", "sets": 3, "reps": 12, "weight": None},
            ],
        },
        {
            "name": "Leg Day",
            "description": "Quadriceps, hamstrings, glutes, and calves workout.",
            "exercises": [
                {"name": "Barbell Back Squat", "sets": 4, "reps": 8, "weight": None},
                {"name": "Romanian Deadlift", "sets": 3, "reps": 10, "weight": None},
                {"name": "Leg Press", "sets": 3, "reps": 12, "weight": None},
                {"name": "Walking Lunge", "sets": 3, "reps": 12, "weight": None},
                {"name": "Leg Curl", "sets": 3, "reps": 12, "weight": None},
                {"name": "Calf Raise", "sets": 4, "reps": 15, "weight": None},
            ],
        },
        {
            "name": "Upper Body",
            "description": "Complete upper body workout targeting chest, back, shoulders, and arms.",
            "exercises": [
                {"name": "Barbell Bench Press", "sets": 4, "reps": 8, "weight": None},
                {"name": "Barbell Bent-Over Row", "sets": 4, "reps": 8, "weight": None},
                {"name": "Overhead Press", "sets": 3, "reps": 10, "weight": None},
                {"name": "Lat Pulldown", "sets": 3, "reps": 10, "weight": None},
                {"name": "Dumbbell Lateral Raise", "sets": 3, "reps": 15, "weight": None},
                {"name": "Barbell Curl", "sets": 3, "reps": 10, "weight": None},
                {"name": "Tricep Pushdown", "sets": 3, "reps": 12, "weight": None},
            ],
        },
        {
            "name": "Lower Body",
            "description": "Complete lower body workout targeting quads, hamstrings, glutes, and calves.",
            "exercises": [
                {"name": "Barbell Back Squat", "sets": 4, "reps": 8, "weight": None},
                {"name": "Romanian Deadlift", "sets": 4, "reps": 8, "weight": None},
                {"name": "Leg Press", "sets": 3, "reps": 12, "weight": None},
                {"name": "Walking Lunge", "sets": 3, "reps": 10, "weight": None},
                {"name": "Leg Curl", "sets": 3, "reps": 12, "weight": None},
                {"name": "Calf Raise", "sets": 4, "reps": 15, "weight": None},
                {"name": "Plank", "sets": 3, "reps": 60, "weight": None},
            ],
        },
        {
            "name": "Full Body",
            "description": "A balanced full body workout hitting all major muscle groups in one session.",
            "exercises": [
                {"name": "Barbell Back Squat", "sets": 3, "reps": 8, "weight": None},
                {"name": "Barbell Bench Press", "sets": 3, "reps": 8, "weight": None},
                {"name": "Barbell Bent-Over Row", "sets": 3, "reps": 8, "weight": None},
                {"name": "Overhead Press", "sets": 3, "reps": 10, "weight": None},
                {"name": "Romanian Deadlift", "sets": 3, "reps": 10, "weight": None},
                {"name": "Barbell Curl", "sets": 2, "reps": 12, "weight": None},
                {"name": "Plank", "sets": 3, "reps": 60, "weight": None},
            ],
        },
    ]

    existing_template_names = {
        t.name
        for t in db.query(WorkoutTemplate.name).filter(WorkoutTemplate.is_system == True).all()
    }

    added = 0
    for tmpl_data in templates_data:
        if tmpl_data["name"] in existing_template_names:
            continue

        template = WorkoutTemplate(
            name=tmpl_data["name"],
            description=tmpl_data.get("description"),
            is_system=True,
            user_id=None,
            usage_count=0,
        )
        db.add(template)
        db.flush()

        for sort_idx, ex_info in enumerate(tmpl_data["exercises"], start=1):
            exercise_id = _get_id(ex_info["name"])
            if exercise_id is None:
                continue

            te = TemplateExercise(
                template_id=template.id,
                exercise_id=exercise_id,
                sort_order=sort_idx,
                default_sets=ex_info["sets"],
                default_reps=ex_info["reps"],
                default_weight=ex_info.get("weight"),
                notes=None,
            )
            db.add(te)

        added += 1

    db.flush()
    print(f"System templates seeded: {added} added, {len(existing_template_names)} already existed.")


if __name__ == "__main__":
    seed_database()