def trim_dupli_name(name):
    # trim last digits of duplicated names e.g. myobj.002
    split_names = name.split('.')
    if len(split_names) > 1:
        last_digits = split_names[len(split_names)-1]
        for i in last_digits:# make sure they're integer, otherwise it shouldn't be a duplicated name
            try: 
                int(i)
                #print('int i', int(i))
            except:
                return name
                
        len_to_trim = len(last_digits) + 1
        return name[:-len_to_trim]
        
    else:
        return name
        

def byte_size(s: str, encoding: str = "utf-8") -> int:
    # get the number of bytes required to store a string
    # using the given encoding (default: UTF-8).    
    return len(s.encode(encoding))