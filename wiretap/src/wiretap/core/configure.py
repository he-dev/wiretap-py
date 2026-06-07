import pathlib


class Configure:
    class Logging:
        @staticmethod
        def from_dict(config: dict):
            """Configures logging and adds TRACE level not defined in the logging module by default."""
            import logging.config
            logging.config.dictConfig(config)

        @staticmethod
        def from_yaml(path: str | pathlib.Path, encoding: str = "utf-8"):
            import yaml
            match path:
                case str():
                    path = pathlib.Path(path)
                case pathlib.Path():
                    pass
                case _:
                    raise TypeError(f"Expected str or pathlib.Path, got {type(path)}")

            with open(path, "r", encoding=encoding) as file:
                config = yaml.safe_load(file)
                # config["handlers"]["elastic_file"]["filename"] = rf"c:\temp\elastic-v8.0.0-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.log"
                Configure.Logging.from_dict(config)

    # class ActivityScope:
    #     @staticmethod
    #     def use_message_composer(composer: str):
    #         pass

    # wiretap.Configure.logging_from_yaml(...)
    # wiretap.Configure.use_message_composer(...)
    # wiretap.Configure.use_validation(...)
