-- Immutable observed GCC image references, not copies of image bytes.
CREATE TABLE IF NOT EXISTS gcc_lot_images (
 lot_id TEXT NOT NULL,
 image_url TEXT NOT NULL CHECK(image_url LIKE 'https://cdn.gradedcardcenter.com/image/%'),
 observed_at TEXT NOT NULL,
 PRIMARY KEY(lot_id,image_url)
) WITHOUT ROWID;
CREATE TRIGGER IF NOT EXISTS gcc_lot_images_no_update BEFORE UPDATE ON gcc_lot_images BEGIN SELECT RAISE(ABORT,'immutable_lot_image'); END;
CREATE TRIGGER IF NOT EXISTS gcc_lot_images_no_delete BEFORE DELETE ON gcc_lot_images BEGIN SELECT RAISE(ABORT,'immutable_lot_image'); END;
