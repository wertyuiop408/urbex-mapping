#python script to harvest info from urban exploring sites and add it to a database so that it can be displayed on a map


from db import db
import xxviii_dayslater as d2l


def main() -> None:
    db.create_tables()
    

    x = d2l.xxviii_dayslater()
    x.crawl()
    
    return

if __name__ == "__main__":
    main()