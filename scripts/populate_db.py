"""Populates the database with some dummy data.

Run with command: `python -m dev_tools.populate_db`

This script should only be run against a local postgres instance.
It sets the `DB_CONNECTION_STRING_SECRET` environment variable to the
local postgres connection string to ensure this.

First, start the local postgres instance with `./dev_tools/start-local-postgres.sh`.
You can run (or not run) this script automatically as the last step of the
`./dev_tools/start-local-postgres.sh` script by supplying the
`--populate/--no-populate` flag to that script. `--populate` is the default.
"""
import os
from datetime import datetime, timedelta, timezone

import clean_energy_api
from clean_energy_api import enums
from clean_energy_api.data_sources.database import datastore, db_models

# DB connection constants
DB_STRING_KEY = "DB_CONNECTION_STRING_SECRET"
LOCAL_DB_CONNECTION_STRING = (
    "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres"
)

# datetime constants
TIMEZONE = timezone.utc
TODAY = datetime.now(tz=TIMEZONE)
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
THREE_DAYS_PAST = TODAY - timedelta(days=3)
THREE_DAYS_FUTURE = TODAY + timedelta(days=3)
LAST_WEEK = TODAY - timedelta(days=7)
NEXT_WEEK = TODAY + timedelta(days=7)


class PopulateDB:
    """Populates the database with dummy data."""

    def __init__(self, session: datastore.Datastore) -> None:
        """Initialize the class."""
        self.session = session
        self.locations = []
        self.clients = []
        self.users = []
        self.pnodes = []
        self.listings = []
        self.projects = []

    def _populate_locations(self) -> None:
        """Populate the locations table."""
        locations = [
            db_models.Location(
                latitude=40.0150,
                longitude=-105.2705,
                city="The Shire",
                state="Eridor",
                country="Middle Earth",
                postal_code="80301",
            ),
            db_models.Location(
                latitude=37.7749,
                longitude=-122.4194,
                city="EastFold",
                state="Gondor",
                country="Middle Earth",
                postal_code="94107",
            ),
            db_models.Location(
                latitude=26.6771,
                longitude=-80.0370,
                city="Mount Doom",
                state="Mordor",
                country="Middle Earth",
                postal_code="33480",
            ),
        ]
        for location in locations:
            self.locations.append(self.session.put(location))

    def _populate_clients(self) -> None:
        """Populate the clients table."""
        clients = [
            db_models.Client(
                id="730bfdf6-01b0-4a1c-97c4-2ac225536cbe",
                name="The Hobbits of the Shire",
                client_code="HotS",
                location_id=self.locations[0].id,
                contact_name="Bilbo Baggins",
                contact_email="bbaggins@shouldakeptaringonit.com",
                contact_phone="555-555-5555",
                image="https://tolkiengateway.net/w/images/4/4b/Ted_Nasmith_-_Green_Hill_Morning.jpg",
            ),
            db_models.Client(
                name="Riders of Rohan",
                client_code="ROR",
                location_id=self.locations[1].id,
                contact_name="Éomer",
                contact_email="horseboy@mylittlepony.com",
                contact_phone="555-555-5556",
                image="https://static.wikia.nocookie.net/lotr/images/b/b9/Eomer_-_Close_up.PNG",
            ),
            db_models.Client(
                name="The Nazgûl",
                client_code="NAZ",
                location_id=self.locations[2].id,
                contact_name="Sauron",
                contact_email="iseeyou@deathbyfire.com",
                contact_phone="666-666-6666",
                image="https://www.sideshow.com/wp/wp-content/uploads/2021/05/Eye-of-Sauron.jpeg",
            ),
        ]
        for client in clients:
            self.clients.append(self.session.put(client))

    def _populate_users(self) -> None:
        """Populate the users table."""
        users = [
            db_models.User(
                id="aea09cbd-db17-48ab-8c2e-1c4b3b0a9768",
                name="Frodo Baggins",
                client_id=self.clients[0].id,
                location_id=self.locations[0].id,
                contact_email="ninefingers@shire.com",
                contact_name="Frodo Baggins",
                contact_phone="555-555-5557",
                buy_isos_preferences=[enums.ISO.ERCOT, enums.ISO.PJM],
                sell_isos_preferences=[enums.ISO.SPP],
            ),
            db_models.User(
                id="d03b00a1-e032-4dad-b482-8341b1da9130",
                name="Gandalf the Grey",
                client_id=self.clients[0].id,
                contact_email="magicman@wizardsrule.com",
                contact_name="Gandalf the Grey",
                contact_phone="555-555-5558",
                buy_isos_preferences=[enums.ISO.ISONE, enums.ISO.NYISO],
                sell_isos_preferences=[enums.ISO.ERCOT, enums.ISO.CAISO],
            ),
            db_models.User(
                id="3b0df3c3-6a3b-417f-9eb0-7b2432deef30",
                name="Aragorn II",
                client_id=self.clients[1].id,
                contact_email="theking@checkmate.com",
                contact_name="Aragorn",
                contact_phone="555-555-5559",
                sell_isos_preferences=[enums.ISO.MISO],
            ),
            db_models.User(
                id="3fd94351-5dcf-4cb4-b998-8469ce8f605d",
                name="Legolas",
                client_id=self.clients[1].id,
                location_id=self.locations[1].id,
                contact_email="arrows@volleyed.com",
                contact_name="Legolas",
                contact_phone="555-555-5560",
                buy_isos_preferences=[enums.ISO.SPP],
            ),
        ]
        for user in users:
            self.users.append(self.session.put(user))

    def _populate_pnodes(self) -> None:
        """Populate the pnodes table."""
        pnodes = [
            db_models.Pnode(
                name="Arnor",
                iso=enums.ISO.ERCOT,
            ),
            db_models.Pnode(
                name="Helm's Deep",
                iso=enums.ISO.ERCOT,
            ),
            db_models.Pnode(
                name="Minas Tirith",
                iso=enums.ISO.SPP,
            ),
            db_models.Pnode(
                name="Barad-dûr",
                iso=enums.ISO.CAISO,
            ),
            db_models.Pnode(
                name="Fangorn",
                iso=enums.ISO.CAISO,
            ),
        ]
        for pnode in pnodes:
            self.pnodes.append(self.session.put(pnode))

    def _populate_listings(self) -> None:
        """Populate the listings table."""
        listings = [
            db_models.Listing(
                client_id=self.clients[1].id,
                name="Rohan Wind",
                status=enums.BiddingStatus.ACCEPT_BINDING,
                start_date=LAST_WEEK,
                end_date=TOMORROW,
                documents_location="https://ascendanalytics.sharepoint.com/sites/ExternalCustomers/CEE_EXAMPLE/Shared%20Documents/DevListing",
                share_location="https://ascendanalytics.sharepoint.com/:f:/s/ExternalCustomers/CEE_EXAMPLE/EtzFgwn_Ma9MmtTldE1kIT8BsyPQp6kascMB1wAPmMUovA?e=46rdvM",
                description="Wind power from Rohan",
                a_estimate=125,
                a_estimate_min=100,
                a_estimate_max=150,
            ),
            db_models.Listing(
                client_id=self.clients[0].id,
                name="Orc Coal",
                status=enums.BiddingStatus.CANCELLED,
                start_date=THREE_DAYS_PAST,
                end_date=THREE_DAYS_FUTURE,
                documents_location="https://ascendanalytics.sharepoint.com/sites/ExternalCustomers/CEE_EXAMPLE/Shared%20Documents/DevListing",
                share_location="https://ascendanalytics.sharepoint.com/:f:/s/ExternalCustomers/CEE_EXAMPLE/EtzFgwn_Ma9MmtTldE1kIT8BsyPQp6kascMB1wAPmMUovA?e=46rdvM",
                description="Coal power plant fueled by the trees of Fangorn Forest",
            ),
        ]
        for listing in listings:
            self.listings.append(self.session.put(listing))

    def _populate_projects(self) -> None:
        """Populate the projects table."""
        projects = [
            db_models.Project(
                location_id=self.locations[1].id,
                listing_id=self.listings[1].id,
                name="Cool Breeze",
                iso=enums.ISO.ERCOT,
                status=enums.ProjectStatus.CONSTRUCTION,
                type=enums.ProjectType.GENERATION,
                cod="2025-05-01",
                ntp="late 2025",
                pnode_id=self.pnodes[0].id,
                proxy=False,
                description="Stiff wind flowing over the plains of Rohan",
                poi=123.45,
            ),
            db_models.Project(
                location_id=self.locations[1].id,
                listing_id=self.listings[0].id,
                name="Horse Power",
                iso=enums.ISO.ERCOT,
                status=enums.ProjectStatus.PRE_NTP,
                type=enums.ProjectType.SHAPED_ENERGY,
                cod="2024-07-04",
                ntp="mid 2024",
                pnode_id=self.pnodes[1].id,
                proxy=True,
                description="Horses of pure energy.",
                poi=13.7,
                min_price_pre_ntp=0.5,
                min_price_ntp=1.25,
                min_price_cod=25,
            ),
            db_models.Project(
                location_id=self.locations[2].id,
                listing_id=self.listings[1].id,
                name="Hot Fire",
                iso=enums.ISO.CAISO,
                status=enums.ProjectStatus.NTP,
                type=enums.ProjectType.GENERATION_PLUS_STORAGE,
                cod="2045-12-25",
                ntp="late 2045",
                pnode_id=self.pnodes[3].id,
                proxy=True,
                description="Fire from the depths of Mordor",
                poi=1.0,
                min_price_pre_ntp=0.54,
                min_price_ntp=666,
                min_price_cod=9001,
            ),
        ]
        for project in projects:
            self.projects.append(self.session.put(project))

    def _populate_project_generation(self) -> None:
        """Populate the project_generation table."""
        project_generation = [
            db_models.ProjectGeneration(
                pid=self.projects[0].id,
                type=enums.GenerationType.WIND,
                capacity=124.7,
                other_detail="Strong winds, but unreliable.",
            ),
            db_models.ProjectGeneration(
                pid=self.projects[2].id,
                type=enums.GenerationType.BIOMASS_BIOGAS,
                capacity=9001.0,
                other_detail="Eternal fire.",
            ),
        ]
        for project_gen in project_generation:
            self.session.put(project_gen)

    def _populate_project_storage(self) -> None:
        """Populate the project_storage table."""
        project_storages = [
            db_models.ProjectStorage(
                pid=self.projects[1].id,
                type=enums.StorageType.COMPRESSED_AIR,
                capacity=101.2,
                duration=8,
                other_detail="Horses are very energetic.",
            ),
            db_models.ProjectStorage(
                pid=self.projects[2].id,
                type=enums.StorageType.FLOW_BATTERIES,
                capacity=666.6,
                duration=6,
                other_detail="This storage rules them all.",
            ),
        ]
        for storage in project_storages:
            self.session.put(storage)

    def _populate_project_development(self) -> None:
        """Populate the project_development table."""
        project_developments = [
            db_models.ProjectDevelopment(
                pid=self.projects[0].id,
                type=enums.DevelopmentType.LAND,
                notes="Rohan is a land of horses and wind.",
                status="Signed lease option",
                status_value=enums.DevelopmentStatus.COMPLETED,
            ),
            db_models.ProjectDevelopment(
                pid=self.projects[0].id,
                type=enums.DevelopmentType.PERMIT,
                notes="The proper paperwork is being filed.",
                status="Horse god ceremony",
                status_value=enums.DevelopmentStatus.IN_PROGRESS,
            ),
            db_models.ProjectDevelopment(
                pid=self.projects[0].id,
                type=enums.DevelopmentType.OFFTAKE,
                status="Take the horses",
                status_value=enums.DevelopmentStatus.IN_PROGRESS,
            ),
            db_models.ProjectDevelopment(
                pid=self.projects[1].id,
                type=enums.DevelopmentType.EPC,
                notes="The horses must be trained.",
                status="Horse training",
                status_value=enums.DevelopmentStatus.NOT_BEGUN,
            ),
            db_models.ProjectDevelopment(
                pid=self.projects[2].id,
                type=enums.DevelopmentType.INTERCONNECTION,
                notes="The fire must be connected to the grid.",
                status="Fire connection",
                status_value=enums.DevelopmentStatus.NOT_BEGUN,
            ),
            db_models.ProjectDevelopment(
                pid=self.projects[2].id,
                type=enums.DevelopmentType.FINANCING,
                notes="Running low on funds. Tax the poor.",
                status="Tax the poor",
                status_value=enums.DevelopmentStatus.NOT_BEGUN,
            ),
        ]
        for development in project_developments:
            self.session.put(development)

    def _populate_listing_docs(self) -> None:
        """Populate the listing_docs table."""
        docs = [
            db_models.ListingDoc(
                pid=self.listings[0].id,
                uploader_id=self.users[0].id,
                uri="https://en.wikipedia.org/wiki/Rohan",
                title="All about Rohan",
                last_updated=YESTERDAY,
                classification=enums.Classification.EXTERNAL,
            ),
            db_models.ListingDoc(
                pid=self.listings[1].id,
                uploader_id=self.users[1].id,
                uri="https://en.wikipedia.org/wiki/Mordor",
                title="All about Mordor",
                last_updated=YESTERDAY,
                classification=enums.Classification.EXTERNAL,
            ),
        ]
        for doc in docs:
            self.session.put(doc)

    def _populate_project_docs(self) -> None:
        """Populate the project_docs table."""
        docs = [
            db_models.ProjectDoc(
                pid=self.projects[0].id,
                uploader_id=self.users[0].id,
                uri="https://cdn.britannica.com/07/4607-050-8A8872A0/Post-windmill-machinery-mill-housing-Agostino-Ramelli-1588.jpg",
                title="Windmill schematic",
                last_updated=LAST_WEEK,
                classification=enums.Classification.EXTERNAL,
            ),
            db_models.ProjectDoc(
                pid=self.projects[1].id,
                uploader_id=self.users[1].id,
                uri="https://ascendanalytics.sharepoint.com/sites/ExternalCustomers/CEE_EXAMPLE/Shared%20Documents/DevListing/Data%20Room/rohan.jpg",
                title="Horse of Sharepoint",
                last_updated=LAST_WEEK,
                classification=enums.Classification.PROPRIETARY,
            ),
            db_models.ProjectDoc(
                pid=self.projects[2].id,
                uploader_id=self.users[2].id,
                uri="https://static.wikia.nocookie.net/middleearthshadowofmordor7723/images/a/a3/Mt_doon_08.jpg",
                title="Mount Doom",
                last_updated=THREE_DAYS_PAST,
                classification=enums.Classification.EXTERNAL,
            ),
        ]
        for doc in docs:
            self.session.put(doc)

    def _populate_bids(self) -> None:
        """Populate the bids table."""
        bids = [
            db_models.Bid(
                lid=self.listings[0].id,
                submitted_date=TODAY,
                submitter=self.users[1].id,
                uri="https://lotr.fandom.com/",
                title="Bid for Wind",
            ),
            db_models.Bid(
                lid=self.listings[0].id,
                submitted_date=YESTERDAY,
                submitter=self.users[2].id,
                uri="https://lotr.fandom.com/",
                title="Bid for Coal",
            ),
        ]
        for bid in bids:
            self.session.put(bid)

    def populate(self) -> None:
        """Populate the database with dummy data."""
        self._populate_locations()
        self._populate_clients()
        self._populate_users()
        self._populate_pnodes()
        self._populate_listings()
        self._populate_projects()
        self._populate_project_generation()
        self._populate_project_storage()
        self._populate_project_development()
        self._populate_project_docs()
        self._populate_listing_docs()
        self._populate_bids()


def populate_database() -> None:
    """Run the populate db script."""
    db_connection_before = os.environ.get(DB_STRING_KEY)
    os.environ[DB_STRING_KEY] = LOCAL_DB_CONNECTION_STRING
    with clean_energy_api.create_app().app_context(), datastore.get_datastore() as session:
        pop_db = PopulateDB(session=session)
        pop_db.populate()
    if db_connection_before:
        os.environ[DB_STRING_KEY] = db_connection_before


if __name__ == "__main__":
    populate_database()
