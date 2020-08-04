import argparse
from array import array


def main(asc_fpath, bin_fpath):

    def parse_asc_header_line(ln, expected_key):
        key, value = ln.strip().split()
        if key != expected_key:
            raise Exception("ASC file is not well formed, unexpected header {}".format(key))
        return value
    
    with open(asc_fpath, 'r') as f:

        # parse header values
        ncols = int(parse_asc_header_line(next(f), 'ncols'))
        nrows = int(parse_asc_header_line(next(f), 'nrows'))
        xllcorner = float(parse_asc_header_line(next(f), 'xllcorner'))
        yllcorner = float(parse_asc_header_line(next(f), 'yllcorner'))
        cellsize = float(parse_asc_header_line(next(f), 'cellsize'))
        nodataval = int(parse_asc_header_line(next(f), 'NODATA_value'))
        xllcenter = xllcorner + (cellsize / 2.0);
        yllcenter = yllcorner + (cellsize / 2.0);
        
        # parse altitude values
        rows = []
        for ln in f.readlines():
            row = ln.strip().split()
            if len(row) != ncols:
                raise Exception("ASC file is not well formed, row length and ncols don't match")
            rows.append([ int(value) for value in row ])
        if len(rows) != nrows:
            raise Exception("ASC file is not well formed, number of rows and nrows don't match")

    with open(bin_fpath, 'wb') as f:

        # write header values
        header_array = array('d', [ncols, nrows, xllcenter, yllcenter, cellsize, nodataval])
        header_array.tofile(f)

        # write altitude values
        for row in rows:
            row_array = array('h', row)
            row_array.tofile(f)
        

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description="Converts SRTM ASCII files to binary format")
    parser.add_argument("srtm_asc", help='[INPUT] SRTM ASCII file. i.e. srtm_36_04.asc')
    parser.add_argument("srtm_bin", help='[OUTPUT] SRTM binary file')
    args = parser.parse_args()

    main(args.srtm_asc, args.srtm_bin)
